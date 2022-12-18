from abc import abstractmethod
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Protocol,
    Tuple,
    Union,
    runtime_checkable,
)

from attrs import field, mutable

from .exceptions import TooFewArgsError, UnexpectedTriggerError
from .type_converters import TypeConverter

EllipsisType = type(...)


@runtime_checkable
class Parameter(Protocol):
    """Protocol class for Parameters."""

    value: Any
    descr: str

    @abstractmethod
    def process(self, args: List[str]) -> List[str]:
        """Get a list of arguments and returns any unused ones."""
        ...


@runtime_checkable
class Option(Parameter, Protocol):
    """Protocol class for Options."""

    triggers: List[str]


@mutable(slots=False)
class BoolOption:
    """Implementation of boolean options."""

    descr: str
    pos_triggers: List[str]
    neg_triggers: List[str]
    value: Union[bool, EllipsisType] = field(default=...)

    @property
    def triggers(self) -> List[str]:
        return self.pos_triggers + self.neg_triggers

    def process(self, args: List[str]) -> List[str]:
        """Process the arguments."""
        # check that we have at least one argument
        if len(args) == 0:
            raise TooFewArgsError("Expected at least one argument, got none.")

        # check that the argument given matches the triggers
        if args[0] in self.pos_triggers:
            self.value = True
        elif args[0] in self.neg_triggers:
            self.value = False
        else:
            raise UnexpectedTriggerError(
                f"Option {args[0]} not registered as a trigger."
            )

        return args[1:]


@mutable(slots=False)
class KnownLenOpt:
    """Base class for options of known length."""

    descr: str
    triggers: Tuple[str, ...]
    nargs: int
    value: Any
    type_converter: TypeConverter
    multiple: bool
    callback: Optional[Callable[[Any], Any]] = field(default=None)
    times_called: int = field(default=0, init=False)

    def __post_init__(self):
        # if multiple is true, it has to be a list
        if self.multiple:
            assert isinstance(self.value, list)

    def process_args(self, args: List[str]) -> None:
        """Process the arguments and store in value."""
        args_value = self.type_converter(*args)
        if self.callback is not None:
            args_value = self.callback(args_value)

        if self.multiple:
            if self.times_called == 0:
                self.value = [args_value]
            else:
                self.value.append(args_value)
        else:
            self.value = args_value

        self.times_called += 1

    def process(self, args: List[str]) -> List[str]:
        """Implement of general argument processing."""
        if len(args) == 0:
            raise TooFewArgsError("Expected at least one argument, got none.")

        if args[0] not in self.triggers:
            raise UnexpectedTriggerError(
                f"Option {args[0]} not registered as a trigger."
            )

        if self.nargs == -1:
            # take all arguments
            self.process_args(args[1:])
            return []

        if len(args) - 1 < self.nargs:
            raise TooFewArgsError(
                f"Expected {self.nargs} arguments but got {len(args) - 1}"
            )

        self.process_args(args[1 : (self.nargs + 1)])
        return args[(self.nargs + 1) :]


def none_converter(*args) -> None:
    """Convert to None."""
    del args
    return None


class NoOpOption(KnownLenOpt):
    """Option that performs no operation."""

    def __init__(self, descr: str, triggers: Tuple[str, ...]):
        """Initialize no-op option."""
        super().__init__(
            descr=descr,
            triggers=triggers,
            nargs=0,
            value=...,
            type_converter=none_converter,
            callback=None,
            multiple=False,
        )


class Arguments(Parameter):
    pass


@mutable(slots=False)
class KnownLenArgs:

    descr: str
    nargs: int
    value: Any
    type_converter: TypeConverter
    callback: Optional[Callable[[Any], Any]] = field(default=None)
    times_called: int = field(default=0, init=False)

    def process_args(self, args: List[str]) -> None:
        """Process the arguments and store in value."""
        args_value = self.type_converter(*args)
        if self.callback is not None:
            args_value = self.callback(args_value)

        self.value = args_value

        self.times_called += 1

    def process(self, args: List[str]) -> List[str]:
        """Implement of general argument processing."""
        if len(args) == 0:
            raise TooFewArgsError("Expected at least one argument, got none.")

        if self.nargs == -1:
            # take all arguments
            self.process_args(args)
            return []

        if len(args) < self.nargs:
            raise TooFewArgsError(
                f"Expected {self.nargs} arguments but got {len(args)}"
            )

        self.process_args(args[: self.nargs])
        return args[self.nargs :]
