"""Utilities for the package."""

from typing import Sequence, Tuple


def clify_argname(x: str) -> str:
    return x.replace("_", "-")


def split_args_by_nargs(
    x: Sequence[str], nargs: int
) -> Tuple[Sequence[str], Sequence[str]]:
    if nargs == -1:
        return (x, [])
    else:
        return (x[0:nargs], x[nargs:])
