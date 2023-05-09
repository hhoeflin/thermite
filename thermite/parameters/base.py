from abc import ABC, abstractmethod
from typing import Any, Dict, List, Sequence, Type

from attrs import field, mutable
from exceptiongroup import ExceptionGroup

from thermite.exceptions import ParameterError, TriggerError
from thermite.signatures import ParameterSignature
from thermite.type_converters import (
    CLIArgConverterBase,
    ListCLIArgConverter,
    split_args_by_nargs,
)

from .processors import (
    ConvertTriggerProcessor,
    MultiConvertTriggerProcessor,
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

    processors: List[TriggerProcessor]

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

    def to_argument(self) -> "Argument":
        # to convert it to an argument, we need a processor of subclass
        # ConvertTriggerProcessor
        type_converter = None
        for proc in self.processors:
            if isinstance(proc, MultiConvertTriggerProcessor):
                type_converter = proc.to_convert_trigger_processor().type_converter
                res_type = proc.res_type
                break
            elif isinstance(proc, ConvertTriggerProcessor):
                type_converter = proc.type_converter  # type: ignore
                res_type = proc.res_type
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
            res_type=res_type,
            type_converter=type_converter,
        )

        return res


@mutable(kw_only=True)
class Argument(Parameter):
    res_type: Type
    type_converter: CLIArgConverterBase

    def process(self, args: Sequence[str]) -> Sequence[str]:
        """Implement of general argument processing."""
        try:
            used_args, ret_args = split_args_by_nargs(
                args, self.type_converter.num_req_args
            )
        except Exception as e:
            self._exceptions.append(e)
            return []

        try:
            self._value = self.type_converter.convert(used_args)
        except Exception as e:
            self._exceptions.append(e)

        return ret_args
