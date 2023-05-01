from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from attrs import field, mutable
from exceptiongroup import ExceptionGroup

from thermite.exceptions import ParameterError, TriggerError
from thermite.help import ArgHelp, OptHelp, ProcessorHelp
from thermite.signatures import ParameterSignature
from thermite.type_converters import (
    CLIArgConverterBase,
    CLIArgConverterSimple,
    ListCLIArgConverter,
)

from .processors import (
    ConvertListTriggerProcessor,
    ConvertTriggerProcessor,
    TriggerProcessor,
)

EllipsisType = type(...)


class OptionError(Exception):
    ...


class ArgumentError(Exception):
    ...


class TriggerUsedError(Exception):
    ...


@mutable(kw_only=True)
class Parameter(ABC, ParameterSignature):
    """Base class for Parameters."""

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
                    f"Multiple errors in {self.name}",
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

    def to_argument(self) -> "Argument":
        # to convert it to an argument, we need a processor of subclass
        # ConvertTriggerProcessor
        type_converter = None
        for proc in self._processors:
            if isinstance(proc, ConvertListTriggerProcessor):
                inner_converter = proc.type_converter
                if not isinstance(inner_converter, CLIArgConverterSimple):
                    raise Exception("Inner type converter needs to be simple")
                type_converter = ListCLIArgConverter(
                    target_type=List[inner_converter._target_type],  # type: ignore
                    inner_converter=proc.type_converter,
                )
                type_str = proc.type_str
                break
            elif isinstance(proc, ConvertTriggerProcessor):
                type_converter = proc.type_converter  # type: ignore
                type_str = proc.type_str
                break

        if type_converter is None:
            raise Exception("Can't convert option to argument")

        res = Argument(
            name=self.name,
            python_kind=self.python_kind,
            cli_kind=self.cli_kind,
            descr=self.descr,
            default_value=self.default_value,
            annot=self.annot,
            type_str=type_str,
            type_converter=type_converter,
        )

        return res


@mutable(kw_only=True)
class Argument(Parameter):
    type_str: str
    type_converter: CLIArgConverterBase

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
