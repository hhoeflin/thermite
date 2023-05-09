from __future__ import annotations

import inspect
import sys
import types
from collections.abc import MutableMapping
from inspect import Signature, classify_class_attrs
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    get_origin,
)

from attrs import field, mutable
from loguru import logger

from thermite.config import Config, Event, EventCallbacks, standardize_obj
from thermite.signatures import extract_descriptions
from thermite.utils import clify_argname

from .parameters import (
    Parameter,
    ParameterGroup,
    process_class_to_param_group,
    process_function_to_param_group,
    process_instance_to_param_group,
)
from .preprocessing import split_and_expand, undeque
from .type_converters import args_used


class UnknownCommandError(Exception):
    ...


@mutable
class CliCallback:
    callback: Callable
    triggers: List[str]
    descr: str
    num_req_args: Union[int, slice] = 0

    def execute(self, cmd: "Command", args: Sequence[str]) -> Optional[Sequence[str]]:
        if args[0] in self.triggers:
            num_args_use = args_used(
                num_offered=len(args) - 1, num_req=self.num_req_args
            )
            self.callback(cmd, *args[1 : (1 + num_args_use)])
            return args[(1 + num_args_use) :]
        else:
            raise Exception("Callback was raised without appropriate trigger.")


@mutable
class Subcommand:
    descr: Optional[str]
    attr_name: str


def extract_subcommands(
    return_type: Any, omit_dunder: bool = True
) -> Dict[str, Subcommand]:
    # First we check if it is a type or a function
    # there are not possilbe, only class instances
    if isinstance(return_type, types.FunctionType):
        raise Exception("Function type not allowed as return object for CLI")
    if get_origin(return_type) == Type:
        raise Exception("Class type is not allowed as return object for CLI")
    if return_type == Signature.empty:
        return {}
    if inspect.isclass(return_type):
        class_attrs = classify_class_attrs(return_type)
        res = {}
        for attr_name, _, _, obj in class_attrs:
            if omit_dunder and attr_name.startswith("__"):
                continue
            descr = extract_descriptions(obj)
            res[clify_argname(attr_name)] = Subcommand(
                descr=descr.short_descr, attr_name=attr_name
            )

        return res
    else:
        return {}


def cb_list_to_trigger_map(cb_list: List[CliCallback]):
    res = {}
    for cb in cb_list:
        for trigger in cb.triggers:
            res[trigger] = cb

    return res


@mutable
class Command(MutableMapping):
    param_group: ParameterGroup
    subcommands: Dict[str, Subcommand]
    config: Config
    prev_cmd: Optional["Command"] = None

    local_cli_callbacks: List[CliCallback] = field(factory=list)

    _history: List[str] = field(init=False, factory=list)

    def __attrs_post_init__(self):
        if len(self.param_group.cli_args) > 0 and len(self.subcommands) > 0:
            raise Exception("Can't have CLI that has subcommands and arguments")

    def __getitem__(self, key) -> Union[Parameter, ParameterGroup]:
        return self.param_group[key]

    def __setitem__(self, key, value):
        self.param_group[key] = value

    def __delitem__(self, key):
        self.param_group.__delitem__(key)

    def __len__(self):
        return len(self.param_group)

    def __iter__(self):
        return self.param_group.__iter__()

    def _add_history(self, input_args: List[str], args_return: List[str]) -> None:
        if len(args_return) > 0:
            if input_args[-len(args_return) :] != args_return:
                # something has changed during processing
                logger.warning(
                    "Non-processed arguments have changed:"
                    f"\ninput: {input_args[-len(args_return):]}"
                    "\nreturned: {args_return}"
                )
        self._history.extend(input_args[: (len(input_args) - len(args_return))])

    @classmethod
    def _from_function(cls, func: Callable, name: str, config: Config):
        param_group = process_function_to_param_group(
            func, config=config, name=name, prefix="", python_kind=None
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(param_group.return_annot),
        )

    @classmethod
    def _from_instance(cls, obj: Any, name: str, config: Config):
        param_group = process_instance_to_param_group(
            obj, config=config, name=name, prefix="", python_kind=None
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(obj.__class__),
        )

    @classmethod
    def _from_class(cls, klass: Type, name: str, config: Config):
        param_group = process_class_to_param_group(
            klass, config=config, name=name, prefix="", python_kind=None
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(klass),
        )

    @classmethod
    def from_obj(cls, obj: Any, name: str, config: Config):
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            res = cls._from_function(func=obj, name=name, config=config)
        elif inspect.isclass(obj):
            res = cls._from_class(obj, name=name, config=config)
        else:
            raise NotImplementedError()

        return res

    def process(self, args: Sequence[str]) -> List[str]:
        cli_args_splitter = self.config.SplitterClass(args, self)

        cb_map = dict(
            **cb_list_to_trigger_map(self.config.cli_callbacks),
            **cb_list_to_trigger_map(self.local_cli_callbacks),
        )

        while (next_args := cli_args_splitter.next()) is not None:
            # first we check if we need to trigger one of the callbacks
            # only if that is not the case do we hand it to the
            # regular parameters; the callbacks are eager and need
            # to be processed first
            if len(next_args) > 0 and next_args[0] in cb_map:
                cb = cb_map[next_args[0]]
                args_return = cb.execute(self, next_args)
                self._add_history(input_args=next_args, args_return=args_return)
                if args_return is not None:
                    cli_args_splitter.add_remain(args_return)
            else:
                args_return = self.param_group.process(next_args)
                self._add_history(input_args=next_args, args_return=args_return)
                if len(args_return) > 0:
                    cli_args_splitter.add_remain(args_return)
                    if len(args_return) == len(next_args):
                        # we are finished
                        return cli_args_splitter.final()
        return []

    def get_subcommand(self, name: str) -> "Command":
        if name in self.subcommands:
            res_obj = self.param_group.value

            # we restrict subcommands to only work with instance objects
            # for now
            if isinstance(res_obj, types.FunctionType):
                raise Exception("Functions not supported as basis for subcommands")

            subcmd = self.subcommands[name]
            if subcmd.attr_name != "":
                subcommand = self.from_obj(
                    getattr(res_obj, subcmd.attr_name), name=name, config=self.config
                )
            else:
                subcommand = self.from_obj(
                    getattr(res_obj, "__call__"), name=name, config=self.config
                )
            subcommand.prev_cmd = self
            # add the command as the last item of the history
            self._add_history([name], [])
            return subcommand
        else:
            raise UnknownCommandError(f"Unknown subcommand {name}")

    @property
    def usage(self) -> str:
        usage_str = sys.argv[0]

        if len(self.param_group.cli_opts) > 0:
            usage_str += " [OPTIONS]"

        if len(self.subcommands) > 0:
            usage_str += " SUBCOMMAND"

        if len(self.param_group.cli_args) > 0:
            usage_str += " ARGS"

        return usage_str

    @property
    def name(self) -> str:
        return self.param_group.name


def match_obj_filter_cmd(
    obj_to_match: Any, cb: Callable[["Command"], "Command"]
) -> Callable[["Command"], "Command"]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(cmd: "Command") -> "Command":
        if standardize_obj(cmd.param_group.obj) == std_obj_to_match:
            return cb(cmd)
        else:
            return cmd

    return filtered_callback


EventCallbacks.default_event_obj_filters[Event.CMD_POST_CREATE] = match_obj_filter_cmd
EventCallbacks.default_event_obj_filters[Event.CMD_POST_PROCESS] = match_obj_filter_cmd
