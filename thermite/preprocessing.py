"Basic processing of command line arguments"
from collections import deque
from itertools import chain
from typing import Deque, List, Sequence

from more_itertools import split_before


def expand_dash_arg(x: str) -> List[str]:
    """
    Expand arguments with single dash and several chars.

    Separate several chars into separate single dash options.
    """
    if x.startswith("-") and not x.startswith("--"):
        return [f"-{char}" for char in x[1:]]
    else:
        return [x]


def split_and_expand(args: Sequence[str]) -> Deque[List[str]]:
    """
    Split command line arguments and expand single dash args.

    Command line arguments are expanded into groups or arguments.
    Each group of arguments is split at an option that starts
    either with a single or a double dash.

    Args:
        args (List[str]): A list of arguments

    Returns:
        A list of lists of arguments. Each list inside the list represnt
        a set of arguments potentially related to an option.

    """
    return deque(
        split_before(
            chain(*[expand_dash_arg(arg) for arg in args]),
            pred=lambda x: x.startswith("-"),
        )
    )
