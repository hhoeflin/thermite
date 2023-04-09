import sys
import textwrap
import traceback
from types import ModuleType
from typing import Iterable, List, Optional, Union

from attrs import asdict, mutable
from exceptiongroup import ExceptionGroup, format_exception_only
from rich.text import Text
from rich.traceback import LOCALS_MAX_LENGTH, LOCALS_MAX_STRING, Traceback

from thermite.rich import console


class ThermiteException(Exception):
    pass


class TriggerError(ThermiteException):
    pass


class ParameterError(ThermiteException):
    pass


class MultiParameterError(ParameterError, ExceptionGroup):
    pass


class UnmatchedOriginError(ThermiteException):
    pass


class IncorrectNumberArgs(ThermiteException):
    pass


class DuplicatedTriggerError(ThermiteException):
    pass


class NothingProcessedError(ThermiteException):
    pass


class TooFewInputsError(ThermiteException):
    pass


class UnspecifiedParameterError(ThermiteException):
    pass


class UnspecifiedOptionError(UnspecifiedParameterError):
    pass


class UnspecifiedArgumentError(UnspecifiedParameterError):
    pass


class UnprocessedArgumentError(ThermiteException):
    pass


class UnknownArgumentError(ThermiteException):
    pass


class UnknownOptionError(ThermiteException):
    pass


def format_exc_with_cause(exc: Exception) -> str:
    res = "".join(format_exception_only(exc))

    if exc.__cause__ is not None:
        sub_res = format_exc_with_cause(exc.__cause__)
        sub_res = textwrap.indent("".join(sub_res), prefix="  ")
        import pudb

        pudb.set_trace()
        res = res + "\nThis exception is caused by:\n" + sub_res

    return res


def thermite_exc_handler(exc: Exception) -> Optional[Exception]:
    if isinstance(exc, ThermiteException):
        console.print(format_exc_with_cause(exc))
        sys.exit(1)
    else:
        return exc


@mutable
class RichExcHandler:
    width: Optional[int] = 100
    extra_lines: int = 3
    theme: Optional[str] = None
    word_wrap: bool = False
    show_locals: bool = True
    locals_max_length: int = LOCALS_MAX_LENGTH
    locals_max_string: int = LOCALS_MAX_STRING
    locals_hide_dunder: bool = True
    locals_hide_sunder: bool = False
    indent_guides: bool = True
    suppress: Iterable[Union[str, ModuleType]] = ()
    max_frames: int = 100

    def __call__(self, exc: Exception) -> Optional[Exception]:
        trace = Traceback.from_exception(
            type(exc), exc, exc.__traceback__, **asdict(self)
        )
        console.print(trace)
        sys.exit(1)
