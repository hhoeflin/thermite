from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Union

from attrs import field, mutable

from thermite.exceptions import (
    UnexpectedTriggerError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
)
from thermite.help import ArgHelp, OptHelp
from thermite.type_converters import CLIArgConverterBase

EllipsisType = type(...)


class OptionError(Exception):
    ...


class ArgumentError(Exception):
    ...


@mutable
class BoundArgs:
    converter: CLIArgConverterBase
    args: Sequence[str]

    def convert(self) -> Any:
        return self.converter.convert(self.args)


@mutable(slots=False, kw_only=True)
class Parameter(ABC):
    """Base class for Parameters."""

    descr: Optional[str] = field(default=None)
    name: str
    default_value: Any

    @property
    @abstractmethod
    def nargs(self) -> int:
        ...

    @abstractmethod
    def bind(self, args: Sequence[str]) -> None:
        """Get a list of arguments and returns any unused ones."""
        ...

    @property
    @abstractmethod
    def unset(self) -> bool:
        ...

    @property
    @abstractmethod
    def target_type_str(self) -> str:
        ...

    @property
    @abstractmethod
    def value(self) -> Any:
        ...


@mutable(slots=False, kw_only=True)
class Option(Parameter):
    """Base class for Options."""

    _prefix: str = ""
    multiple: bool = False

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str):
        self._prefix = prefix

    @property
    @abstractmethod
    def final_trigger_mappings(self) -> Dict[str, "Option"]:
        ...

    @property
    @abstractmethod
    def final_trigger_help(self) -> str:
        ...

    def _adjust_triggers(self, triggers: Set[str]) -> Set[str]:
        if self.prefix == "":
            return set(triggers)
        else:
            filtered_triggers = filter(lambda x: x.startswith("--"), triggers)
            return set(
                [f"--{self.prefix}-{trigger[2:]}" for trigger in filtered_triggers]
            )

    def help(self) -> OptHelp:
        default_str = str(self.default_value) if self.default_value != ... else ""

        return OptHelp(
            triggers=self.final_trigger_help,
            type_descr=self.target_type_str,
            default=default_str,
            descr=self.descr if self.descr is not None else "",
        )


@mutable(slots=False, kw_only=True)
class BoolOption(Option):
    """Implementation of boolean options."""

    pos_triggers: Set[str] = field(converter=set)
    neg_triggers: Set[str] = field(converter=set)
    _value: Union[bool, EllipsisType] = field(default=...)  # type: ignore

    @property
    def nargs(self) -> int:
        return 1

    @property
    def unset(self) -> bool:
        return self._value == ...

    @property
    def final_pos_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.pos_triggers)

    @property
    def final_neg_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.neg_triggers)

    @property
    def final_trigger_mappings(self) -> Dict[str, Option]:
        return {x: self for x in (self.final_pos_triggers | self.final_neg_triggers)}

    @property
    def final_trigger_help(self):
        return (
            f"{', '.join(self.final_pos_triggers)} / "
            f"{', '.join(self.final_neg_triggers)}"
        )

    def bind(self, args: Sequence[str]) -> None:
        """Process the arguments."""
        # check that we have at least one argument, the trigger
        if self.nargs != -1 and len(args) != self.nargs:
            raise OptionError(
                f"Incorrect number of arguments. Expected {self.nargs} "
                f"but got {len(args)}."
            )

        if self.unset or self.multiple:
            # check that the argument given matches the triggers
            if args[0] in self.final_pos_triggers:
                self._value = True
            elif args[0] in self.final_neg_triggers:
                self._value = False
            else:
                raise UnexpectedTriggerError(
                    f"Option {args[0]} not registered as a trigger."
                )
        else:
            raise Exception("Multiple calls not allowed")

    @property
    def target_type_str(self) -> str:
        return "Bool"

    @property
    def value(self) -> bool:
        if self.unset:
            if self.default_value == ...:
                raise UnspecifiedOptionError(
                    f"Paramter {self.name} was not specified and has no default"
                )
            else:
                return self.default_value
        else:
            return self._value


@mutable(slots=False, kw_only=True)
class KnownLenOpt(Option):
    """Base class for options of known length."""

    triggers: Set[str] = field(converter=set)
    _target_type_str: str
    type_converter: CLIArgConverterBase
    _bound_args_list: List[BoundArgs] = field(init=False, factory=list)

    def __attrs_post_init__(self):
        # if multiple is true, it has to be a list
        if self.multiple:
            assert isinstance(self.value, list)

    @property
    def nargs(self) -> int:
        if self.type_converter.num_required_args.min == -1:
            return -1
        else:
            return self.type_converter.num_required_args.min + 1

    @property
    def unset(self) -> bool:
        return len(self._bound_args_list) == 0

    @property
    def final_trigger_mappings(self) -> Dict[str, Option]:
        return {x: self for x in self._adjust_triggers(self.triggers)}

    @property
    def final_trigger_help(self) -> str:
        return f"{', '.join(self.final_trigger_mappings.keys())}"

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        if self.unset or self.multiple:
            self._bound_args_list.append(BoundArgs(self.type_converter, args))
        else:
            raise Exception("Multiple calls not allowed")

    def bind(self, args: Sequence[str]) -> None:
        """Implement of general argument processing."""
        if self.nargs != -1 and len(args) != self.nargs:
            raise OptionError(
                f"Incorrect number of arguments. Expected {self.nargs} "
                f"but got {len(args)}."
            )

        if args[0] not in self.final_trigger_mappings:
            raise UnexpectedTriggerError(
                f"Option {args[0]} not registered as a trigger."
            )

        self._process_args(args[1:])

    @property
    def target_type_str(self) -> str:
        return self._target_type_str

    @target_type_str.setter
    def target_type_str(self, value: str):
        self._target_type_str = value

    @property
    def value(self) -> Any:
        if self.unset:
            if self.default_value == ...:
                raise UnspecifiedOptionError(
                    f"Paramter {self.name} was not specified and has no default"
                )
            else:
                return self.default_value
        else:
            if self.multiple:
                return [x.convert() for x in self._bound_args_list]
            else:
                return self._bound_args_list[0].convert()


@mutable(slots=False, kw_only=True)
class Argument(Parameter):
    def help(self) -> ArgHelp:
        default_str = str(self.default_value) if self.default_value != ... else ""
        return ArgHelp(
            name=self.name,
            type_descr=self.target_type_str,
            default=default_str,
            descr=self.descr if self.descr is not None else "",
        )


@mutable(slots=False, kw_only=True)
class KnownLenArg(Argument):

    _target_type_str: str
    callback: Optional[Callable[[Any], Any]] = field(default=None)
    type_converter: CLIArgConverterBase
    _bound_args: Optional[BoundArgs] = None

    @property
    def nargs(self) -> int:
        return self.type_converter.num_required_args.max

    @property
    def unset(self) -> bool:
        return self._bound_args is None

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        if self.unset:
            self._bound_args = BoundArgs(self.type_converter, args)
        else:
            raise Exception("Multiple calls not allowed")

    def bind(self, args: Sequence[str]) -> None:
        """Implement of general argument processing."""
        if self.nargs != -1 and len(args) != self.nargs:
            raise ArgumentError(
                f"Incorrect number of arguments. Expected {self.nargs} "
                f"but got {len(args)}."
            )

        self._process_args(args)

    @property
    def target_type_str(self) -> str:
        return self._target_type_str

    @target_type_str.setter
    def target_type_str(self, value: str):
        self._target_type_str = value

    @property
    def value(self) -> Any:
        if self.unset:
            if self.default_value == ...:
                raise UnspecifiedArgumentError(
                    f"Paramter {self.name} was not specified and has no default"
                )
            else:
                return self.default_value
        else:
            return self._bound_args.convert()  # type: ignore
