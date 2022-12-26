from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Sequence, Set, Union

from attrs import field, mutable

from thermite.exceptions import (
    TooFewInputsError,
    UnexpectedTriggerError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
    UnspecifiedParameterError,
)
from thermite.type_converters import TypeConverter

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class Parameter(ABC):
    """Base class for Parameters."""

    descr: str = field(default="")
    name: str = field(default="")
    _num_splits_processed: int = field(default=0, init=False)
    _value: Any = field(default=...)

    @abstractmethod
    def process_split(self, args: Sequence[str]) -> List[str]:
        """Get a list of arguments and returns any unused ones."""
        ...

    @property
    @abstractmethod
    def value(self) -> Any:
        ...

    @property
    def unset(self) -> bool:
        return self._num_splits_processed == 0


@mutable(slots=False, kw_only=True)
class Option(Parameter):
    """Base class for Options."""

    _prefix: str = ""

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

    @property
    def value(self) -> Any:
        if self._value == ...:
            raise UnspecifiedOptionError(
                f"Paramter {self.name} was not specified and has no default"
            )
        return self._value

    def _adjust_triggers(self, triggers: Set[str]) -> Set[str]:
        if self.prefix == "":
            return set(triggers)
        else:
            filtered_triggers = filter(lambda x: x.startswith("--"), triggers)
            return set(
                [f"--{self.prefix}-{trigger[2:]}" for trigger in filtered_triggers]
            )


@mutable(slots=False, kw_only=True)
class BoolOption(Option):
    """Implementation of boolean options."""

    pos_triggers: Set[str] = field(converter=set)
    neg_triggers: Set[str] = field(converter=set)
    _value: Union[bool, EllipsisType] = field(default=...)  # type: ignore

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

        return list(args[1:])


@mutable(slots=False, kw_only=True)
class KnownLenOpt(Option):
    """Base class for options of known length."""

    triggers: Set[str] = field(converter=set)
    nargs: int
    type_converter: TypeConverter
    multiple: bool
    callback: Optional[Callable[[Any], Any]] = field(default=None)

    def __attrs_post_init__(self):
        # if multiple is true, it has to be a list
        if self.multiple:
            assert isinstance(self.value, list)

    @property
    def final_triggers(self) -> Set[str]:
        return self._adjust_triggers(self.triggers)

    @property
    def final_trigger_help(self) -> str:
        return f"{', '.join(self.final_triggers)}"

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        args_value = self.type_converter(*args)
        if self.callback is not None:
            args_value = self.callback(args_value)

        if self.multiple:
            if self._num_splits_processed == 0:
                self._value = [args_value]
            else:
                self._value.append(args_value)
        else:
            self._value = args_value

        self._num_splits_processed += 1

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


def none_converter(*args) -> None:
    """Convert to None."""
    del args
    return None


class NoOpOption(KnownLenOpt):
    """Option that performs no operation."""

    def __init__(self, descr: str, triggers: Set[str]):
        """Initialize no-op option."""
        super().__init__(
            descr=descr,
            triggers=set(triggers),  # type: ignore
            nargs=0,
            value=...,
            type_converter=none_converter,
            callback=None,
            multiple=False,
        )


@mutable(slots=False, kw_only=True)
class Argument(Parameter):
    @property
    def value(self) -> Any:
        if self._value == ...:
            raise UnspecifiedArgumentError(
                f"Paramter {self.name} was not specified and has no default"
            )
        return self._value


@mutable(slots=False, kw_only=True)
class KnownLenArg(Argument):

    nargs: int
    type_converter: TypeConverter
    callback: Optional[Callable[[Any], Any]] = field(default=None)

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        args_value = self.type_converter(*args)
        if self.callback is not None:
            args_value = self.callback(args_value)

        self._value = args_value

        self._num_splits_processed += 1

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
