from typing import Any, Callable, ClassVar, Dict, Optional, Sequence

from attrs import field, mutable

from thermite.exceptions import (
    NothingProcessedError,
    UnexpectedReturnTypeError,
    UnprocessedArgumentError,
)
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

    @classmethod
    def from_obj(cls, obj: Any):
        pass

    def process_multiple(self, args: Sequence[str]) -> Any:
        input_args_deque = split_and_expand(args)

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            try:
                args_return = self.param_group.process(input_args)
            except NothingProcessedError:
                # there are arguments left that the param_group can't handle
                # search through the subcommand_objs
                if input_args[0] in self.subcommand_objs:
                    # get a subcommand, hand all remaining arguments to it
                    input_args_deque.appendleft(input_args[1:])
                    remaining_input_args = list(input_args_deque)
                    input_args_deque.clear()

                    res_obj = self.obj(
                        *self.param_group.args, **self.param_group.kwargs
                    )

                    if not isinstance(res_obj, self.expected_ret_type):  # type: ignore
                        raise UnexpectedReturnTypeError(
                            f"Expected return type {str(self.expected_ret_type)} "
                            f"but got {str(type(res_obj))}"
                        )

                    subcommand = self.from_obj(self.subcommand_objs[input_args[0]])
                    return subcommand.process_multiple(remaining_input_args)
                else:
                    raise UnprocessedArgumentError(
                        f"Argument {args} could not be processed"
                    )
            if len(args_return) == len(input_args):
                raise Exception("Input args have same length as return args")
            if len(args_return) > 0:
                input_args_deque.appendleft(args_return)
