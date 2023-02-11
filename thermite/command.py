import inspect
import sys
import types
from inspect import Signature
from typing import Any, Callable, ClassVar, Dict, List, Optional, Sequence, Type

from attrs import mutable

from thermite.help import CommandHelp

from .exceptions import UnprocessedArgumentError
from .parameters import (
    ParameterGroup,
    process_class_to_param_group,
    process_function_to_param_group,
)
from .preprocessing import split_and_expand, undeque
from .type_converters import CLIArgConverterStore


def extract_subcommands(return_type: Any) -> Dict[str, Any]:
    if return_type == Signature.empty:
        return {}
    else:
        return {}


class UnknownCommandError(Exception):
    ...


@mutable()
class Callback:
    callback: Callable[["Command"], None]
    triggers: List[str]


@mutable
class Subcommand:
    descr: str
    attr_name: str


# Supported combinations of subcommand-types and return-values
# Property:
# - class is supported
# - instance is supported (wrap the creation into a function
#       with 0 arguments and correctly annotated return value
# - function is supported

# method: (class or instance)
# - Class is not supported
# - instance is supported
# - function is not supported
#
# function: same as method


@mutable(slots=False)
class Command:
    name: str
    param_group: ParameterGroup
    subcommands: Dict[str, str]
    prev_cmd: Optional["Command"] = None

    global_callbacks: ClassVar[List[Callback]] = []
    store: ClassVar[CLIArgConverterStore] = CLIArgConverterStore(add_defaults=True)

    @classmethod
    def _from_function(cls, func: Callable, name: str):

        param_group = process_function_to_param_group(func, store=cls.store)
        return cls(
            name=name,
            param_group=param_group,
            subcommands={},
        )

    @classmethod
    def _from_instance(cls, obj: Any, name: str):
        # an instance would only provide additional subcommands, without
        # any options
        ...

    @classmethod
    def _from_class(cls, klass: Type, name: str):
        param_group = process_class_to_param_group(klass, store=cls.store)
        # TODO: Need to add subcommand_objs
        # all classmethods and object-methods will be subcommands
        methods_dict = [
            attr
            for attr in dir(klass)
            if callable(getattr(klass, attr)) and attr.startswith("__") is False
        ]

        return cls(
            name=name,
            param_group=param_group,
            subcommands={},
        )

    @classmethod
    def from_obj(cls, obj: Any, name: str):
        if inspect.isfunction(obj):
            return cls._from_function(func=obj, name=name)
        elif inspect.isclass(obj):
            return cls._from_class(obj, name=name)
        else:
            raise NotImplementedError()

    def bind(self, args: Sequence[str]) -> List[str]:
        input_args_deque = split_and_expand(args)
        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            args_return = self.param_group.bind(input_args)
            if args_return is not None:
                input_args_deque.appendleft(list(args_return))
                if len(args_return) == len(input_args):
                    # we are finished
                    return undeque(input_args_deque)
        return []

    def subcommand(self, name: str) -> "Command":
        if name in self.subcommands.items():
            res_obj = self.param_group.value

            # we restrict subcommands to only work with instance objects
            # for now
            if type(res_obj) == types.FunctionType:
                raise Exception("Functions not supported as basis for subcommands")

            attr_name = self.subcommands[name]
            if attr_name != "":
                subcommand = self.from_obj(getattr(res_obj, attr_name), name=name)
            else:
                subcommand = self.from_obj(getattr(res_obj, "__call__"), name=name)
            subcommand.prev_cmd = self

            return subcommand
        else:
            raise UnknownCommandError(f"Unknown subcommand {name}")

    @property
    def usage(self) -> str:
        return "Not yet implemented"

    def help(self) -> CommandHelp:
        # argument help to show
        args = [x.help() for x in self.param_group.cli_args]

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
            opt_group=opt_group,
            subcommands=subcommands,
        )


def process_all_args(input_args: List[str], cmd: Command) -> Any:
    """
    Processes all input arguments in the context of a command.

    The arguments are processes for the current command, and then
    followed up with further processing in subcommands as needed.
    """
    ...
    # Note how to do eager callbacks?
    # how to do lazy callbacks?
    while len(input_args) > 0:
        input_args = cmd.bind(input_args)
        if len(input_args) > 0:
            try:
                cmd = cmd.subcommand(input_args[0])
            except UnknownCommandError:
                raise UnprocessedArgumentError(
                    f"Arguments {input_args} could not be processed"
                )
            input_args = input_args[1:]
        else:
            return cmd.param_group.value


def run(
    obj: Any,
    store: Optional[CLIArgConverterStore] = None,
    callbacks: Optional[List[Callback]] = None,
) -> Any:
    if store is not None:
        Command.store = store

    if callbacks is not None:
        Command.global_callbacks = callbacks
    cmd = Command.from_obj(obj, name=sys.argv[0])
    # get all input arguments
    input_args = sys.argv[1:]
    return process_all_args(input_args=input_args, cmd=cmd)
