from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type

import pytest

from thermite.exceptions import (
    NothingProcessedError,
    UnexpectedTriggerError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
)
from thermite.parameters import ParameterGroup
from thermite.preprocessing import split_and_expand
from thermite.process_objects import process_function
from thermite.type_converters import (
    ComplexTypeConverterFactory,
    SimpleTypeConverterFactory,
)


def example_func_kw_or_pos(a: int, b: str = "1") -> Tuple[int, str]:
    """
    This is an example function

    Params:
        a: An integer
        b: a string

    """
    return (a, b)


def example_func_pos_only(a: int, b: str = "1", /) -> Tuple[int, str]:
    """
    This is an example function

    Params:
        a: An integer
        b: a string

    """
    return (a, b)


def process_multiple(input_args_multiple: Sequence[str], param_group: ParameterGroup):
    input_args_deque = split_and_expand(input_args_multiple)

    while len(input_args_deque) > 0:
        input_args = input_args_deque.popleft()
        args_return = param_group.process(input_args)
        if len(args_return) == len(input_args):
            raise Exception("Input args have same length as return args")
        if len(args_return) > 0:
            input_args_deque.appendleft(args_return)


class TestProcessFunctions:
    complex_factory = ComplexTypeConverterFactory(SimpleTypeConverterFactory())

    @pytest.mark.parametrize(
        "func,input_args,process_exc,output_args,output_kwargs",
        [
            (
                example_func_kw_or_pos,
                ("--a", "1", "--b", "test"),
                None,
                (),
                {"a": 1, "b": "test"},
            ),
            (
                example_func_kw_or_pos,
                ("1", "test"),
                NothingProcessedError,
                (),
                {},
            ),
            (
                example_func_kw_or_pos,
                ("--b", "test"),
                UnspecifiedOptionError,
                (),
                {},
            ),
            (
                example_func_pos_only,
                ("1", "test"),
                None,
                (1, "test"),
                {},
            ),
            (
                example_func_pos_only,
                ("--a", "1", "--b", "test"),
                UnexpectedTriggerError,
                (),
                {},
            ),
            (
                example_func_pos_only,
                (),
                UnspecifiedArgumentError,
                (),
                {},
            ),
        ],
    )
    def test_value(
        self,
        func: Callable,
        input_args: Sequence[str],
        process_exc: Optional[Type],
        output_args: Optional[Tuple[Any]],
        output_kwargs: Optional[Dict[str, Any]],
    ):
        param_group = process_function(func, self.complex_factory)

        if process_exc is not None:
            with pytest.raises(process_exc):
                process_multiple(input_args, param_group=param_group)
                assert param_group.args == output_args
                assert param_group.kwargs == output_kwargs
        else:
            process_multiple(input_args, param_group=param_group)
            assert param_group.args == output_args
            assert param_group.kwargs == output_kwargs
