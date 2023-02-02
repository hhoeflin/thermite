import inspect
from inspect import Signature
from typing import Any, Callable, ClassVar, Dict, List, Sequence, Type

from attrs import mutable

from thermite.help import CommandHelp

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


@mutable(slots=False)
class Command:
    param_group: ParameterGroup
    subcommand_objs: Dict[str, Any]

    _store: ClassVar[CLIArgConverterStore] = CLIArgConverterStore(add_defaults=True)

    @classmethod
    def _from_function(cls, func: Callable):

        param_group = process_function_to_param_group(func, store=cls._store)
        return cls(
            param_group=param_group,
            subcommand_objs={},
        )

    @classmethod
    def _from_class(cls, klass: Type):
        param_group = process_class_to_param_group(klass, store=cls._store)

        return cls(
            param_group=param_group,
            subcommand_objs={},
        )

    @classmethod
    def from_obj(cls, obj: Any):
        if inspect.isfunction(obj):
            return cls._from_function(func=obj)
        elif inspect.isclass(obj):
            return cls._from_class(obj)
        else:
            raise NotImplementedError()

    def bind_split(self, args: Sequence[str]) -> List[str]:
        input_args_deque = split_and_expand(args)
        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            args_return = self.param_group.bind_split(input_args)
            if len(args_return) == len(input_args):
                # we are finished
                input_args_deque.appendleft(list(args_return))
                return undeque(input_args_deque)
            if len(args_return) > 0:
                # push the remaining args back and do another round
                input_args_deque.appendleft(list(args_return))
        return []

    def subcommand(self, name: str) -> "Command":
        if name in self.subcommand_objs:
            res_obj = self.param_group.value
            subcommand = self.from_obj(getattr(res_obj, name))

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
        subcommands = {key: obj.descr for key, obj in self.subcommand_objs.items()}

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
    # Note how to do eagery callbacks?
    # how to do lazy callbacks?
    while len(input_args) > 0:
        input_args = cmd.bind_split(input_args)
        if len(input_args) > 0:
            cmd = cmd.subcommand(input_args[0])
            input_args = input_args[1:]
        else:
            return cmd.param_group.value
