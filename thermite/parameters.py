from abc import ABC, abstractmethod
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from attrs import field, mutable

from .exceptions import (
    DuplicatedTriggerError,
    TooFewInputsError,
    TooManyInputsError,
    UnexpectedTriggerError,
)
from .type_converters import TypeConverter

EllipsisType = type(...)


class Parameter(ABC):
    """Protocol class for Parameters."""

    value: Any
    descr: str

    @abstractmethod
    def process(self, args: Sequence[str]) -> List[str]:
        """Get a list of arguments and returns any unused ones."""
        ...


@mutable(slots=False, kw_only=True)
class Option(Parameter):
    """Protocol class for Options."""

    prefix: str = ""

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


@mutable(slots=False)
class BoolOption(Option):
    """Implementation of boolean options."""

    descr: str
    pos_triggers: Set[str] = field(converter=set)
    neg_triggers: Set[str] = field(converter=set)
    value: Union[bool, EllipsisType] = field(default=...)  # type: ignore

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

    def process(self, args: Sequence[str]) -> List[str]:
        """Process the arguments."""
        # check that we have at least one argument
        if len(args) == 0:
            raise TooFewInputsError("Expected at least one input argument, got none.")

        # check that the argument given matches the triggers
        if args[0] in self.final_pos_triggers:
            self.value = True
        elif args[0] in self.final_neg_triggers:
            self.value = False
        else:
            raise UnexpectedTriggerError(
                f"Option {args[0]} not registered as a trigger."
            )

        return list(args[1:])


@mutable(slots=False)
class KnownLenOpt(Option):
    """Base class for options of known length."""

    descr: str
    triggers: Set[str] = field(converter=set)
    nargs: int
    value: Any
    type_converter: TypeConverter
    multiple: bool
    callback: Optional[Callable[[Any], Any]] = field(default=None)
    times_called: int = field(default=0, init=False)

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
            if self.times_called == 0:
                self.value = [args_value]
            else:
                self.value.append(args_value)
        else:
            self.value = args_value

        self.times_called += 1

    def process(self, args: Sequence[str]) -> List[str]:
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
    times_called: int = field(default=0, init=False)


@mutable(slots=False)
class KnownLenArg(Argument):

    descr: str
    nargs: int
    value: Any
    type_converter: TypeConverter
    callback: Optional[Callable[[Any], Any]] = field(default=None)

    def _process_args(self, args: Sequence[str]) -> None:
        """Process the arguments and store in value."""
        args_value = self.type_converter(*args)
        if self.callback is not None:
            args_value = self.callback(args_value)

        self.value = args_value

        self.times_called += 1

    def process(self, args: Sequence[str]) -> List[str]:
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


@mutable(slots=False)
class OptionGroup:
    descr: str
    _prefix: str
    _name: str
    _opts: Dict[str, Option] = field(factory=dict, init=False)
    _stored_trigger_mapping: Optional[Dict[str, Option]] = field(
        default=None, init=False
    )

    def _set_prefix_children(self):
        for option in self._options.values():
            option.prefix = self.child_prefix

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str):
        self._prefix = prefix
        self._set_prefix_children()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self._set_prefix_children()

    @property
    def child_prefix(self) -> str:
        if self.prefix != "":
            return f"{self.prefix}-{self.name}"
        else:
            return self.name

    def mapping_final_trigger_to_opt(self) -> Dict[str, Option]:
        res: Dict[str, Option] = {}
        for opt in self._opts.values():
            final_triggers = opt.final_triggers
            for trigger in final_triggers:
                if trigger in res:
                    raise DuplicatedTriggerError(
                        f"Trigger {trigger} in options {opt} and {res[trigger]}"
                    )
                else:
                    res[trigger] = opt
        return res

    def final_triggers(self) -> Set[str]:
        return set(self.mapping_final_trigger_to_opt().keys())

    def process(self, args: Sequence[str]) -> List[str]:
        if self._stored_trigger_mapping is None:
            self._stored_trigger_mapping = self.mapping_final_trigger_to_opt()

        if len(args) == 0:
            raise TooFewInputsError("Processing options requires more than 0 args.")

        if not args[0].startswith("-"):
            raise Exception("First argument has to start with a '-': {args[0]}")

        if args[0] in self._stored_trigger_mapping:
            return self._stored_trigger_mapping[args[0]].process(args)
        else:
            raise UnexpectedTriggerError(f"Trigger {args[0]} not in mapping")

    def add_opt(self, name: str, option: Option):
        # ensure that the new option has the right prefix
        if name in self._opts:
            raise Exception(f"{name} already a stored option.")
        option.prefix = self.child_prefix
        self._opts[name] = option

    @property
    def kwargs(self) -> Dict[str, Any]:
        return {key: opt.value for key, opt in self._opts.items()}


@mutable(slots=False)
class ArgumentGroup:
    _args: Dict[str, Argument] = field(factory=dict, init=False)

    def add_arg(self, name: str, argument: Argument):
        # ensure that the new option has the right prefix
        if name in self._args:
            raise Exception(f"{name} already a stored argument.")
        self._args[name] = argument

    def process(self, args: Sequence[str]) -> List[str]:
        if len(args) == 0:
            raise TooFewInputsError("Processing options requires more than 0 args.")

        if args[0].startswith("-"):
            raise Exception("First argument can't be a trigger: {args[0]}")

        # go through the stored arguments to the first unprocessed one
        for argument in self._args.values():
            if argument.times_called == 0:
                return argument.process(args)

        raise TooManyInputsError(f"No remaining unspecified argument for {args}")

    @property
    def args(self) -> Tuple[Any, ...]:
        return tuple((arg.value for arg in self._args.values()))


@mutable(slots=False)
class ParameterGroup:
    descr: str
    _arg_group: ArgumentGroup = field(factory=ArgumentGroup, init=False)
    _opt_group: OptionGroup = field(
        factory=partial(OptionGroup, descr="", prefix="", name=""), init=False
    )

    def add_param(self, name: str, param: Parameter):
        if isinstance(param, Argument):
            self._arg_group.add_arg(name, param)
        elif isinstance(param, Option):
            self._opt_group.add_opt(name, param)
        else:
            raise TypeError(f"Unknown type {type(param)}")

    def process(self, args: Sequence[str]) -> List[str]:
        if len(args) == 0:
            return []

        if args[0].startswith("-"):
            return self._opt_group.process(args)
        else:
            return self._arg_group.process(args)

    @property
    def args(self) -> Tuple[Any, ...]:
        return self._arg_group.args

    @property
    def kwargs(self) -> Dict[str, Any]:
        return self._opt_group.kwargs
