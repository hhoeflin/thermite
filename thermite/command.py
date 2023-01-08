import inspect
from inspect import Signature
from typing import Any, Callable, ClassVar, Dict, Sequence, Type

from attrs import mutable

from .exceptions import NothingProcessedError, UnprocessedArgumentError
from .parameters import (
    ParameterGroup,
    process_class_to_param_group,
    process_function_to_param_group,
)
from .preprocessing import split_and_expand
from .type_converters import ComplexTypeConverterFactory


def extract_subcommands(return_type: Any) -> Dict[str, Any]:
    if return_type == Signature.empty:
        return {}
    else:
        return {}


@mutable(slots=False)
class Command:
    param_group: ParameterGroup
    subcommand_objs: Dict[str, Any]

    _complex_factory: ClassVar[
        ComplexTypeConverterFactory
    ] = ComplexTypeConverterFactory()

    @classmethod
    def _from_function(cls, func: Callable):

        param_group = process_function_to_param_group(
            func, complex_factory=cls._complex_factory
        )
        return cls(
            param_group=param_group,
            subcommand_objs={},
        )

    @classmethod
    def _from_class(cls, klass: Type):
        param_group = process_class_to_param_group(
            klass, complex_factory=cls._complex_factory
        )

        return cls(
            param_group=param_group,
            subcommand_objs={},
        )

    @classmethod
    def from_obj(cls, obj: Any):
        if inspect.isfunction(obj):
            return cls._from_function(func=obj)
        elif inspect.isclass(obj):
            return cls._from_class(obj)
        else:
            raise NotImplementedError()

    def process_multiple(self, args: Sequence[str]) -> Any:
        input_args_deque = split_and_expand(args)

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            try:
                args_return = self.param_group.process_split(input_args)
            except NothingProcessedError:
                # there are arguments left that the param_group can't handle
                # search through the subcommand_objs
                if input_args[0] in self.subcommand_objs:
                    # get a subcommand, hand all remaining arguments to it
                    input_args_deque.appendleft(input_args[1:])
                    remaining_input_args = list(input_args_deque)
                    input_args_deque.clear()

                    res_obj = self.param_group.value

                    subcommand = self.from_obj(getattr(res_obj, input_args[0]))
                    return subcommand.process_multiple(remaining_input_args)
                else:
                    raise UnprocessedArgumentError(
                        f"Argument {args} could not be processed"
                    )
            if len(args_return) == len(input_args):
                raise Exception("Input args have same length as return args")
            if len(args_return) > 0:
                input_args_deque.appendleft(args_return)
        return self.param_group.value
