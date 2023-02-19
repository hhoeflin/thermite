from pathlib import Path
from typing import Union

import pytest

from thermite.utils import ClassContentType, analyze_class, clean_type_str


class A:
    @staticmethod
    def a():
        pass

    @classmethod
    def b(cls):
        pass

    def c(self):
        pass

    @property
    def d(self):
        pass

    e = 0


def test_analyze_class():
    assert analyze_class(A) == {
        "a": ClassContentType.staticmethod,
        "b": ClassContentType.classmethod,
        "c": ClassContentType.instancemethod,
        "d": ClassContentType.property,
        "e": ClassContentType.classvar,
    }


def test_clean_type_str():
    assert clean_type_str(int) == "int"
    assert clean_type_str(Union[int, Path]) == "Union[int, Path]"
