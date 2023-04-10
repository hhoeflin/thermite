from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Set

from attrs import field, mutable
from exceptiongroup import ExceptionGroup

from thermite.exceptions import ParameterError, TriggerError
from thermite.help import ArgHelp, OptHelp, ProcessorHelp
from thermite.type_converters import CLIArgConverterBase

from .processors import TriggerProcessor

EllipsisType = type(...)


class OptionError(Exception):
    ...


class ArgumentError(Exception):
    ...


class TriggerUsedError(Exception):
    ...


@mutable(kw_only=True)
class Parameter(ABC):
    """Base class for Parameters."""

    descr: Optional[str] = field(default=None)
    name: str
    default_value: Any
    _value: Any = field(default=..., init=False)  # type: ignore
    _exceptions: List[Exception] = field(factory=list, init=False)

    @abstractmethod
    def process(self, args: Sequence[str]) -> Sequence[str]:
        """Get a list of arguments and returns any unused ones."""
        ...

    @property
    def unset(self) -> bool:
        return self._value == ... and len(self._exceptions) == 0

    @property
    def is_required(self) -> bool:
        return self.default_value == ...

    @property
    def value(self) -> Any:
        if len(self._exceptions) > 0:
            if len(self._exceptions) == 1:
                raise self._exceptions[0]
            else:
                raise ExceptionGroup(
                    f"Multiple errors in {self.__class__.__name__}",
                    self._exceptions,
                )
        elif self._value != ...:
            return self._value
        else:
            # unset
            if self.default_value == ...:
                raise ParameterError(
                    f"Paramter {self.name} was not specified and has no default"
                )
            else:
                return self.default_value


@mutable(kw_only=True)
class Option(Parameter):
    """Base class for Options."""

    _prefix: str = ""
    _processors: List[TriggerProcessor]

    def __attrs_post_init__(self):
        self._set_processor_prefix()

    def _set_processor_prefix(self):
        for processor in self.processors:
            processor.prefix = self._prefix

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str):
        self._prefix = prefix
        self._set_processor_prefix()

    @property
    def processors(self) -> List[TriggerProcessor]:
        return self._processors

    @property
    def _final_trigger_by_processor(self) -> Dict[str, TriggerProcessor]:
        res = {}
        for processor in self.processors:
            res.update({trigger: processor for trigger in processor.triggers})
        return res

    @property
    def final_triggers(self) -> Sequence[str]:
        return list(self._final_trigger_by_processor.keys())

    def process(self, args: Sequence[str]) -> Sequence[str]:
        """Implement of general argument processing."""
        trigger_by_processor = self._final_trigger_by_processor
        if len(args) == 0:
            raise TriggerError("A trigger is expected for options.")

        if args[0] not in trigger_by_processor:
            raise TriggerError(f"Option {args[0]} not registered as a trigger.")

        processor = trigger_by_processor[args[0]]
        try:
            ret_args = processor.bind(args)
        except Exception as e:
            self._exceptions.append(e)
            return []

        try:
            self._value = processor.process(self._value)
        except Exception as e:
            self._exceptions.append(e)

        return ret_args

    def help(self) -> OptHelp:
        default_str = str(self.default_value) if self.default_value != ... else ""

        return OptHelp(
            processors=[
                ProcessorHelp(triggers=", ".join(x.triggers), type_descr=x.type_str)
                for x in self.processors
            ],
            default=default_str,
            descr=self.descr if self.descr is not None else "",
        )


@mutable(kw_only=True)
class Argument(Parameter):
    type_str: str
    type_converter: CLIArgConverterBase

    @property
    def nargs(self) -> int:
        return self.type_converter.num_required_args.max

    def process(self, args: Sequence[str]) -> Sequence[str]:
        """Implement of general argument processing."""
        try:
            num_req_args = self.type_converter.num_requested_args(len(args))
            bound_args = args[:num_req_args]
            ret_args = args[num_req_args:]
        except Exception as e:
            self._exceptions.append(e)
            return []

        try:
            self._value = self.type_converter.convert(bound_args)
        except Exception as e:
            self._exceptions.append(e)

        return ret_args

    def help(self) -> ArgHelp:
        default_str = str(self.default_value) if self.default_value != ... else ""
        return ArgHelp(
            name=self.name,
            type_descr=self.type_str,
            default=default_str,
            descr=self.descr if self.descr is not None else "",
        )
