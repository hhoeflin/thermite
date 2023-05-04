from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Type

from attrs import field, mutable

from thermite.exceptions import TriggerError
from thermite.type_converters import CLIArgConverterBase


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

    def bind(self, args: Sequence[str]) -> Sequence[str]:
        if len(args) == 0:
            raise TriggerError("A trigger is expected.")
        if args[0] not in self.triggers:
            raise TriggerError(f"Trigger {args[0]} not an allowed trigger.")

        num_req_args = self.type_converter.num_requested_args(len(args) - 1)

        self.bound_args = args[1 : (1 + num_req_args)]
        return args[(1 + num_req_args) :]


@mutable(kw_only=True)
class ConvertReplaceTriggerProcessor(ConvertTriggerProcessor):
    def process(self, value: Any) -> Any:
        del value
        return self.type_converter.convert(self.bound_args)


@mutable(kw_only=True)
class ConvertOnceTriggerProcessor(ConvertTriggerProcessor):
    def process(self, value: Any) -> Any:
        if value != ...:
            raise TriggerError("Trigger already used once.")
        return self.type_converter.convert(self.bound_args)


@mutable(kw_only=True)
class ConvertListTriggerProcessor(ConvertTriggerProcessor):
    def process(self, value: Any) -> Any:
        append_val = self.type_converter.convert(self.bound_args)
        if not isinstance(value, list):
            return [append_val]
        else:
            value = value.copy()
            value.append(append_val)
            return value
