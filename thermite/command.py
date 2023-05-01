from __future__ import annotations

import inspect
import sys
import types
from collections.abc import MutableMapping
from inspect import Signature, classify_class_attrs
from typing import (
    TYPE_CHECKING,
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

from thermite.help import CbHelp, CommandHelp, extract_descriptions
from thermite.utils import clify_argname

if TYPE_CHECKING:
    from . import config

from .parameters import (
    Parameter,
    ParameterGroup,
    process_class_to_param_group,
    process_function_to_param_group,
    process_instance_to_param_group,
)
from .preprocessing import split_and_expand, undeque


class UnknownCommandError(Exception):
    ...


@mutable
class Callback:
    callback: Callable[["Command"], None]
    triggers: List[str]
    descr: str

    def execute(self, cmd: "Command", args: Sequence[str]) -> Optional[Sequence[str]]:
        if args[0] in self.triggers:
            self.callback(cmd)
        if len(args) > 1:
            return args[1:]
        else:
            return None

    def help(self) -> CbHelp:
        return CbHelp(triggers=", ".join(self.triggers), descr=self.descr)


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


def cb_list_to_trigger_map(cb_list: List[Callback]):
    res = {}
    for cb in cb_list:
        for trigger in cb.triggers:
            res[trigger] = cb

    return res


@mutable
class Command(MutableMapping):
    param_group: ParameterGroup
    subcommands: Dict[str, Subcommand]
    config: "config.Config"
    prev_cmd: Optional["Command"] = None

    local_callbacks: List[Callback] = field(factory=list)

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

    @classmethod
    def _from_function(cls, func: Callable, name: str, config: "config.Config"):
        param_group = process_function_to_param_group(
            func, store=config.stores.cli_args, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(param_group._expected_ret_type),
        )

    @classmethod
    def _from_instance(cls, obj: Any, name: str, config: "config.Config"):
        param_group = process_instance_to_param_group(
            obj, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(obj.__class__),
        )

    @classmethod
    def _from_class(cls, klass: Type, name: str, config: "config.Config"):
        param_group = process_class_to_param_group(
            klass, store=config.stores.cli_args, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            config=config,
            subcommands=extract_subcommands(klass),
        )

    @classmethod
    def from_obj(cls, obj: Any, name: str, config: "config.Config"):
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            res = cls._from_function(func=obj, name=name, config=config)
        elif inspect.isclass(obj):
            res = cls._from_class(obj, name=name, config=config)
        else:
            raise NotImplementedError()

        if obj in config.stores.cmd_post_process:
            return config.stores.cmd_post_process[obj](res)
        else:
            return res

    def process(self, args: Sequence[str]) -> List[str]:
        input_args_deque = split_and_expand(args)

        cb_map = dict(
            **cb_list_to_trigger_map(self.config.callbacks),
            **cb_list_to_trigger_map(self.local_callbacks),
        )

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()

            # first we check if we need to trigger one of the callbacks
            # only if that is not the case do we hand it to the
            # regular parameters; the callbacks are eager and need
            # to be processed first
            if len(input_args) > 0 and input_args[0] in cb_map:
                cb = cb_map[input_args[0]]
                args_return = cb.execute(self, input_args)
                if args_return is not None:
                    input_args_deque.appendleft(list(args_return))
            else:
                args_return = self.param_group.process(input_args)
                if len(args_return) > 0:
                    input_args_deque.appendleft(list(args_return))
                    if len(args_return) == len(input_args):
                        # we are finished
                        return undeque(input_args_deque)
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

    def help(self) -> CommandHelp:
        # argument help to show
        args = [x.help() for x in self.param_group.cli_args]
        cbs = [x.help() for x in self.config.callbacks + self.local_callbacks]

        # the options don't need a special name or description;
        # that is intended for subgroups
        opt_group = self.param_group.help_opts_only()
        opt_group.name = "Options"
        opt_group.descr = None

        # last we need the subcommands and their descriptions
        subcommands = {key: obj.descr for key, obj in self.subcommands.items()}

        return CommandHelp(
            descr=self.param_group.descr,
            usage=self.usage,
            args=args,
            callbacks=cbs,
            opt_group=opt_group,
            subcommands=subcommands,
        )
