from typing import Any, Callable, ClassVar, Dict, Optional, Sequence

from attrs import field, mutable

from thermite.parameters import ParameterGroup
from thermite.preprocessing import split_and_expand
from thermite.process_objects import process_function
from thermite.type_converters import ComplexTypeConverterFactory


@mutable(slots=False)
class Command:
    obj: Any
    param_group: ParameterGroup
    subcommand_objs: Dict[Optional[str], Any]
    expected_ret_type: object

    _complex_factory: ClassVar[ComplexTypeConverterFactory] = field(
        init=False, default=ComplexTypeConverterFactory()
    )

    @classmethod
    def from_function(cls, func: Callable):
        return cls(
            obj=func,
            param_group=process_function(func, complex_factory=cls._complex_factory),
            subcommand_objs={},
            expected_ret_type=Any,
        )

    def process_multiple(self, args: Sequence[str]) -> Any:
        input_args_deque = split_and_expand(args)

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            args_return = self.param_group.process(input_args)
            if len(args_return) == len(input_args):
                raise Exception("Input args have same length as return args")
            if len(args_return) > 0:
                input_args_deque.appendleft(args_return)
