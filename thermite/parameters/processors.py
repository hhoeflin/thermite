from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Type

from attrs import field, mutable

from thermite.exceptions import TriggerError
from thermite.type_converters import (
    CLIArgConverterBase,
    ListCLIArgConverter,
    split_args_by_nargs,
)


def str_list_conv(x: Sequence[str]) -> List[str]:
    return list(x)


@mutable(kw_only=True)
class TriggerProcessor(ABC):
    triggers: List[str] = field(converter=str_list_conv)
    res_type: Type

    @abstractmethod
    def bind(self, args: Sequence[str]) -> Sequence[str]:
        pass

    @abstractmethod
    def process(self, value: Any) -> Any:
        pass


@mutable(kw_only=True)
class ConstantTriggerProcessor(TriggerProcessor):
    constant: Any

    def bind(self, args: Sequence[str]) -> Sequence[str]:
        if len(args) == 0:
            raise TriggerError("A trigger is expected.")
        if args[0] not in self.triggers:
            raise TriggerError(f"Trigger {args[0]} not an allowed trigger.")
        return args[1:]

    def process(self, value: Any) -> Any:
        del value
        return self.constant


@mutable(kw_only=True)
class ConvertTriggerProcessor(TriggerProcessor):
    type_converter: CLIArgConverterBase
    bound_args: Sequence[str] = field(factory=list, init=False)
    allow_replace: bool = False

    def bind(self, args: Sequence[str]) -> Sequence[str]:
        if len(args) == 0:
            raise TriggerError("A trigger is expected.")
        if args[0] not in self.triggers:
            raise TriggerError(f"Trigger {args[0]} not an allowed trigger.")

        bound_args, ret_args = split_args_by_nargs(
            args[1:], num_req_args=self.type_converter.num_req_args
        )

        self.bound_args = bound_args
        return ret_args

    def process(self, value: Any) -> Any:
        if value != ... and not self.allow_replace:
            raise TriggerError("Trigger already used once.")
        return self.type_converter.convert(self.bound_args)


@mutable(kw_only=True)
class MultiConvertTriggerProcessor(TriggerProcessor):
    type_converter: CLIArgConverterBase
    bound_args: Sequence[str] = field(factory=list, init=False)

    def bind(self, args: Sequence[str]) -> Sequence[str]:
        if len(args) == 0:
            raise TriggerError("A trigger is expected.")
        if args[0] not in self.triggers:
            raise TriggerError(f"Trigger {args[0]} not an allowed trigger.")

        bound_args, ret_args = split_args_by_nargs(
            args[1:], num_req_args=self.type_converter.num_req_args
        )

        self.bound_args = bound_args
        return ret_args

    def process(self, value: Any) -> Any:
        append_val = self.type_converter.convert(self.bound_args)
        if not isinstance(value, list):
            return [append_val]
        else:
            value = value.copy()
            value.append(append_val)
            return value

    def to_convert_trigger_processor(self) -> ConvertTriggerProcessor:
        inner_converter = self.type_converter
        if not isinstance(inner_converter.num_req_args, int):
            raise Exception(
                "Inner type converter needs ask for constant number " "of arguments"
            )
        return ConvertTriggerProcessor(
            type_converter=ListCLIArgConverter(
                target_type=List[inner_converter.target_type],  # type: ignore
                inner_converter=inner_converter,
            ),
            triggers=self.triggers,
            res_type=self.res_type,
        )
