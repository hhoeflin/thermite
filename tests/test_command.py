from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type, Union

import pytest
from examples.app import NestedClass, func_kw_or_pos, func_pos_only, func_with_nesting
from rich.console import Console

from thermite.command import Command
from thermite.exceptions import (
    UnexpectedTriggerError,
    UnprocessedArgumentError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
)


@pytest.mark.parametrize(
    "obj,input_args,process_exc,output_args,output_kwargs",
    [
        (
            func_kw_or_pos,
            ("--a", "1", "--b", "test"),
            None,
            (),
            {"a": 1, "b": "test"},
        ),
        (
            func_kw_or_pos,
            ("1", "test"),
            UnprocessedArgumentError,
            (),
            {},
        ),
        (
            func_kw_or_pos,
            ("--b", "test"),
            UnspecifiedOptionError,
            (),
            {},
        ),
        (
            func_pos_only,
            ("1", "test"),
            None,
            (1, "test"),
            {},
        ),
        (
            func_pos_only,
            ("--a", "1", "--b", "test"),
            UnexpectedTriggerError,
            (),
            {},
        ),
        (
            func_pos_only,
            (),
            UnspecifiedArgumentError,
            (),
            {},
        ),
        (
            NestedClass,
            ("--a", "1", "--b", "test"),
            None,
            (),
            {"a": 1, "b": "test"},
        ),
        (
            func_with_nesting,
            ("--nested-a", "1", "--nested-b", "test", "--integer", "2"),
            None,
            (),
            {"nested": NestedClass(a=1, b="test"), "integer": 2},
        ),
    ],
)
def test_command_single_step(
    obj: Union[Callable, Type],
    input_args: Sequence[str],
    process_exc: Optional[Type],
    output_args: Optional[Tuple[Any]],
    output_kwargs: Optional[Dict[str, Any]],
):
    command = Command.from_obj(obj=obj, name="test")

    if process_exc is not None:
        with pytest.raises(process_exc):
            res = command.bind(input_args)
            if len(res) > 0:
                raise UnprocessedArgumentError()
            assert command.param_group.args_values == output_args
            assert command.param_group.kwargs_values == output_kwargs
    else:
        command.bind(input_args)
        assert command.param_group.args_values == output_args
        assert command.param_group.kwargs_values == output_kwargs


if __name__ == "__main__":
    command = Command.from_obj(ExampleNested, name="ExampleNested")
    console = Console()
    console.print(command.help())
