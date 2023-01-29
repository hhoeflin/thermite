from enum import Enum
from pathlib import Path
from typing import Any, List, Literal, Sequence, Tuple, Type, Union

import pytest

from thermite.type_converters import CLIArgConverterStore

enum_test = Enum("test", ["a", "b", "2"])

args_tests = [  # type: ignore
    (int, ["1"], 1, 1),
    (int, ["1.1"], None, 1),
    (int, ["a"], None, 1),
    (float, ["1.0"], 1.0, 1),
    (float, ["a"], None, 1),
    (bool, ["True"], True, 1),
    (bool, ["False"], False, 1),
    (bool, ["true"], True, 1),
    (bool, ["false"], False, 1),
    (bool, ["t"], True, 1),
    (bool, ["f"], False, 1),
    (bool, ["yes"], True, 1),
    (bool, ["no"], False, 1),
    (bool, ["a"], None, 1),
    (Path, ["a"], Path("a"), 1),
    (str, ["a"], "a", 1),
    (Literal["a", "b"], ["a"], "a", 1),
    (Literal["a", "b"], ["b"], "b", 1),
    (Literal["a", "b"], ["c"], None, 1),
    (enum_test, ["a"], enum_test.a, 1),
    (enum_test, ["b"], enum_test.b, 1),
    (enum_test, ["c"], None, 1),
    (Union[enum_test, int], ["a"], enum_test.a, 1),
    (Union[enum_test, int], ["1"], 1, 1),
    (Union[enum_test, int], ["2"], enum_test["2"], 1),
    (Union[enum_test, int], ["1.1"], None, 1),
    (Tuple[int, str], ["2", "yes"], (2, "yes"), 2),
    (Tuple[int, str], ["a", "yes"], None, 2),
    (Tuple[int, str], ["a"], None, 2),
    (List[int], ["1", "2"], [1, 2], -1),
    (List[int], [], [], -1),
    (List[int], ["a", "2"], None, -1),
]


@pytest.mark.parametrize("target_type,args,expected,nargs", args_tests)
def test_store(
    store: CLIArgConverterStore,
    target_type: Type,
    args: List[str],
    expected: Any,
    nargs: int,
):
    converter = store.get_converter(target_type)
    assert converter.num_required_args == nargs
    if expected is not None:
        converter.bind(args)
        res = converter.value
        assert res == expected
    else:
        with pytest.raises(Exception):
            converter.bind(args)
            converter.value
