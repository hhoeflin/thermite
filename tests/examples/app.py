"""App that consists of a top-level function."""
from typing import Literal, Tuple, Union

from attrs import mutable


def func_kw_or_pos(a: int, b: str = "1") -> Tuple[int, str]:
    """
    This is an example function

    Params:
        a: An integer
        b: a string

    """
    return (a, b)


def func_pos_only(a: int, b: str = "1", /) -> Tuple[int, str]:
    """
    This is an example function

    Params:
        a: An integer
        b: a string

    """
    return (a, b)


@mutable(slots=False, kw_only=True)
class NestedClass:
    """A nested data class with some methods."""

    a: int
    b: str = "test"

    @classmethod
    def clsmethod(cls, c: bool):
        del c

    @property
    def value(self):
        return self.a

    def method(self):
        return self.b


def single_level_function(integer: int, string: str, int_or_string: Union[int, str]):
    """
    Simple function that prints its arguments.

    Args:
        integer: An integer
        string: A string
        int_or_string: Could be integer or string
    """
    print((integer, string, int_or_string))


class Subcommands:
    """
    Performing actions on the arguments.
    """

    def __init__(self, integer: int, string: str):

        """
        Initialize the class.

        Args:
            integer: An integer
            string: A string
        """
        self.integer = integer
        self.string = string

    def show_integer(self):
        """Show the integer"""
        print(self.integer)

    def show_string(self):
        """Show the string"""
        print(self.string)

    def show(self, which: Literal["integer", "string"]):
        """
        Decide to show either integer or string.

        Args:
            which:
        """
        if which == "integer":
            print(self.integer)
        elif which == "string":
            print(self.string)
        else:
            raise Exception("Unknonwn 'which'")


def subcommands_function(
    integer: int, string: str, int_or_string: Union[int, str]
) -> Subcommands:
    """
    Calling the subcommand class with the arguments.

    This combines the passed integers and strings as appropriate.
    If 'int_or_string' is an int, it will be added to the integer,
    otherwise concatenated to the string.

    Args:
        integer: An integer
        string: A string
        int_or_string: An integer or string

    Returns:
        An instace of class 'Subcommands'

    """
    if isinstance(int_or_string, int):
        return Subcommands(integer=integer + int_or_string, string=string)
    else:
        return Subcommands(integer=integer, string=string + int_or_string)


def func_with_nesting(nested: NestedClass, integer: int) -> None:
    """
    Function that has a nested subclass

    Args:
        nested: The nested data class
        integer: An integer
    """
    del nested
    del integer


class Aggregation:
    """A collection of functions and classes."""

    single_level_function = single_level_function
    subcommands_function = subcommands_function
    Subcommands = Subcommands
