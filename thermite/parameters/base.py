from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Sequence, Set, Union

from attrs import field, mutable

from thermite.exceptions import (
    TooFewInputsError,
    UnexpectedTriggerError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
)
from thermite.help import ArgHelp, OptHelp
from thermite.type_converters import CLIArgConverterBase

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class Parameter(ABC):
    """Base class for Parameters."""

    descr: Optional[str] = field(default=None)
    name: str
    default_value: Any
    _num_splits_processed: int = field(default=0, init=False)

    @property
    @abstractmethod
    def nargs(self) -> int:
        ...

    @abstractmethod
    def process_split(self, args: Sequence[str]) -> List[str]:
        """Get a list of arguments and returns any unused ones."""
        ...

    @property
    def unset(self) -> bool:
        return self._num_splits_processed == 0

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
    def final_triggers(self) -> Set[str]:
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
        return 0

    @property
    def final_pos_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.pos_triggers)

    @property
    def final_neg_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.neg_triggers)

    @property
    def final_triggers(self) -> Set[str]:
        return self.final_pos_triggers | self.final_neg_triggers

    @property
    def final_trigger_help(self):
        return (
            f"{', '.join(self.final_pos_triggers)} / "
            f"{', '.join(self.final_neg_triggers)}"
        )

    def process_split(self, args: Sequence[str]) -> List[str]:
        """Process the arguments."""
        # check that we have at least one argument
        if len(args) == 0:
            raise TooFewInputsError("Expected at least one input argument, got none.")

        if self._num_splits_processed == 0 or self.multiple:
            # check that the argument given matches the triggers
            if args[0] in self.final_pos_triggers:
                self._value = True
            elif args[0] in self.final_neg_triggers:
                self._value = False
            else:
                raise UnexpectedTriggerError(
                    f"Option {args[0]} not registered as a trigger."
                )
            self._num_splits_processed += 1
        else:
            raise Exception("Multiple calls not allowed")

        return list(args[1:])

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

    def __attrs_post_init__(self):
        # if multiple is true, it has to be a list
        if self.multiple:
            assert isinstance(self.value, list)

    @property
    def nargs(self) -> int:
        return self.type_converter.num_required_args.min

    @property
    def final_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.triggers)

    @property
    def final_trigger_help(self) -> str:
        return f"{', '.join(self.final_triggers)}"

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        if self._num_splits_processed == 0 or self.multiple:
            self.type_converter.bind(args)
            self._num_splits_processed += 1
        else:
            raise Exception("Multiple calls not allowed")

    def process_split(self, args: Sequence[str]) -> List[str]:
        """Implement of general argument processing."""
        if len(args) == 0:
            raise TooFewInputsError("Expected at least one argument, got none.")

        if args[0] not in self.final_triggers:
            raise UnexpectedTriggerError(
                f"Option {args[0]} not registered as a trigger."
            )

        if self.nargs == -1:
            # take all arguments
            self._process_args(args[1:])
            return []

        if len(args) - 1 < self.nargs:
            raise TooFewInputsError(
                f"Expected {self.nargs} arguments but got {len(args) - 1}"
            )

        self._process_args(args[1 : (self.nargs + 1)])
        return list(args[(self.nargs + 1) :])

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
            return self.type_converter.value


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

    @property
    def nargs(self) -> int:
        return self.type_converter.num_required_args.max

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        if self._num_splits_processed == 0:
            self.type_converter.bind(args)
            self._num_splits_processed += 1
        else:
            raise Exception("Multiple calls not allowed")

    def process_split(self, args: Sequence[str]) -> List[str]:
        """Implement of general argument processing."""
        if len(args) == 0:
            raise TooFewInputsError("Expected at least one argument, got none.")

        if self.nargs == -1:
            # take all arguments
            self._process_args(args)
            return []

        if len(args) < self.nargs:
            raise TooFewInputsError(
                f"Expected {self.nargs} arguments but got {len(args)}"
            )
        self._process_args(args[: self.nargs])
        return list(args[self.nargs :])

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
            return self.type_converter.value
