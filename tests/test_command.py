from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type, Union

import pytest

from thermite.command import Command
from thermite.exceptions import (
    UnexpectedTriggerError,
    UnprocessedArgumentError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
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


class ExampleClassKwOnly:
    def __init__(self, a: int, b: str = "test"):
        self.a = a
        self.b = b

    @classmethod
    def clsmethod(cls, c: bool):
        pass

    @property
    def value(self):
        return self.a

    def method(self):
        return self.b


class TestCommandFromFunction:
    @pytest.mark.parametrize(
        "obj,input_args,process_exc,output_args,output_kwargs",
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
                UnprocessedArgumentError,
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
            (
                ExampleClassKwOnly,
                ("--a", "1", "--b", "test"),
                None,
                (),
                {"a": 1, "b": "test"},
            ),
        ],
    )
    def test_value(
        self,
        obj: Union[Callable, Type],
        input_args: Sequence[str],
        process_exc: Optional[Type],
        output_args: Optional[Tuple[Any]],
        output_kwargs: Optional[Dict[str, Any]],
    ):
        command = Command.from_obj(obj=obj)

        if process_exc is not None:
            with pytest.raises(process_exc):
                command.process_multiple(input_args)
                assert command.param_group.args == output_args
                assert command.param_group.kwargs == output_kwargs
        else:
            command.process_multiple(input_args)
            assert command.param_group.args == output_args
            assert command.param_group.kwargs == output_kwargs
