from enum import Enum
from pathlib import Path
from typing import Any, List, Literal, Sequence, Tuple, Type, Union

import pytest

from thermite.type_converters import (
    ComplexTypeConverterFactory,
    SimpleTypeConverterFactory,
)

enum_test = Enum("test", ["a", "b", "2"])

simple_test_args = [
    (int, "1", 1),
    (int, "1.1", None),
    (int, "a", None),
    (float, "1.0", 1.0),
    (float, "a", None),
    (bool, "True", True),
    (bool, "False", False),
    (bool, "true", True),
    (bool, "false", False),
    (bool, "t", True),
    (bool, "f", False),
    (bool, "yes", True),
    (bool, "no", False),
    (bool, "a", None),
    (Path, "a", Path("a")),
    (str, "a", "a"),
    (Literal["a", "b"], "a", "a"),
    (Literal["a", "b"], "b", "b"),
    (Literal["a", "b"], "c", None),
    (enum_test, "a", enum_test.a),
    (enum_test, "b", enum_test.b),
    (enum_test, "c", None),
    (Union[enum_test, int], "a", enum_test.a),
    (Union[enum_test, int], "1", 1),
    (Union[enum_test, int], "2", enum_test["2"]),
    (Union[enum_test, int], "1.1", None),
]


@pytest.mark.parametrize("target_type,arg,expected", simple_test_args)
def test_simple_type_converter_factory(target_type: Type, arg: str, expected: Any):
    simple_factory = SimpleTypeConverterFactory()
    converter = simple_factory.converter_factory(target_type)
    if expected is not None:
        res = converter(arg)
        assert res == expected
    else:
        with pytest.raises(ValueError):
            converter(arg)


complex_test_args: List[Tuple[Any, List, Any, int]] = [
    (Tuple[int, str], ["2", "yes"], (2, "yes"), 2),
    (Tuple[int, str], ["a", "yes"], None, 2),
    (Tuple[int, str], ["a"], None, 2),
    (List[int], ["1", "2"], [1, 2], -1),
    (List[int], [], [], -1),
    (List[int], ["a", "2"], None, -1),
]

all_test_args: List[Any] = [
    (target_type, [arg], expected, 1) for target_type, arg, expected in simple_test_args
] + complex_test_args


# complex types should also work for simple types
@pytest.mark.parametrize("target_type,args,expected,nargs", all_test_args)
def test_complex_type_converter_factory(
    target_type: Type, args: Sequence[str], expected: Any, nargs: int
):
    complex_factory = ComplexTypeConverterFactory(SimpleTypeConverterFactory())
    converter = complex_factory.converter_factory(target_type)
    if expected is not None:
        assert converter.nargs == nargs
        res = converter(*args)
        assert res == expected
    else:
        with pytest.raises(ValueError):
            converter(*args)
