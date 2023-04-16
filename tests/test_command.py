from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

import pytest

from thermite.callbacks import help_callback
from thermite.command import Command
from thermite.config import Config
from thermite.exceptions import (
    ParameterError,
    TriggerError,
    UnprocessedArgumentError,
    UnspecifiedArgumentError,
    UnspecifiedOptionError,
)
from thermite.run import run

from .examples import (
    NestedClass,
    Subcommands,
    func_kw_or_pos,
    func_pos_only,
    func_with_nesting,
    subcommands_function,
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
            ParameterError,
            (),
            {},
        ),
        (
            func_pos_only,
            ("--a", "1", "--b", "test"),
            None,
            (1, "test"),
            {},
        ),
        (
            func_pos_only,
            (),
            ParameterError,
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
def test_command_process(
    obj: Union[Callable, Type],
    input_args: Sequence[str],
    process_exc: Optional[Type],
    output_args: Optional[Tuple[Any]],
    output_kwargs: Optional[Dict[str, Any]],
):
    command = Command.from_obj(obj=obj, name="test", config=Config())

    if process_exc is not None:
        with pytest.raises(process_exc):
            res = command.process(input_args)
            if len(res) > 0:
                raise UnprocessedArgumentError()
            assert command.param_group.args_values == output_args
            assert command.param_group.kwargs_values == output_kwargs
    else:
        command.process(input_args)
        assert command.param_group.args_values == output_args
        assert command.param_group.kwargs_values == output_kwargs


@pytest.mark.parametrize(
    "obj,input_args,process_exc,subcommands",
    [
        (
            func_kw_or_pos,
            ("--a", "1", "--b", "test"),
            None,
            [],
        ),
        (
            Subcommands,
            ("--integer", "1", "--string", "test"),
            None,
            ["show-integer", "show-string", "show"],
        ),
        (
            subcommands_function,
            ("--integer", "1", "--string", "test", "--int-or-string", "2"),
            None,
            ["show-integer", "show-string", "show"],
        ),
    ],
)
def test_command_subcommands(
    obj: Union[Callable, Type],
    input_args: Sequence[str],
    process_exc: Optional[Type],
    subcommands: List[str],
):
    command = Command.from_obj(obj=obj, name="test", config=Config())

    if process_exc is not None:
        with pytest.raises(process_exc):
            res = command.process(input_args)
            if len(res) > 0:
                raise UnprocessedArgumentError()
            assert set(command.subcommands.keys()) == set(subcommands)
    else:
        command.process(input_args)
        assert set(command.subcommands.keys()) == set(subcommands)
