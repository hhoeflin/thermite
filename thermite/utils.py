"""Utilities for the package."""

from enum import Enum
from typing import Dict, Sequence, Tuple, Type


def clify_argname(x: str) -> str:
    return x.replace("_", "-")


def split_args_by_nargs(
    x: Sequence[str], nargs: int
) -> Tuple[Sequence[str], Sequence[str]]:
    if nargs == -1:
        return (x, [])
    else:
        return (x[0:nargs], x[nargs:])


class ClassContentType(Enum):
    classmethod = "classmethod"
    instancemethod = "instancemethod"
    staticmethod = "staticmethod"
    property = "property"
    classvar = "classvar"
    instancevar = "instancevar"


def analyze_class(klass: Type, omit_dunder: bool = True) -> Dict[str, ClassContentType]:
    attr_list = [attr for attr in dir(klass)]
    if omit_dunder:
        attr_list = list(filter(lambda x: not x.startswith("__"), attr_list))

    res = {}
    for attr_name in attr_list:
        attr = klass.__dict__[attr_name]
        if isinstance(attr, staticmethod):
            res[attr_name] = ClassContentType.staticmethod
        elif isinstance(attr, classmethod):
            res[attr_name] = ClassContentType.classmethod
        elif isinstance(attr, property):
            res[attr_name] = ClassContentType.property
        else:
            if callable(attr):
                res[attr_name] = ClassContentType.instancemethod
            else:
                res[attr_name] = ClassContentType.classvar
    return res
