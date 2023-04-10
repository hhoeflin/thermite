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


def remove_tb(exc: Exception) -> Exception:
    if exc.__cause__ is not None:
        exc.__cause__ = remove_tb(exc.__cause__)  # type: ignore

    if isinstance(exc, ExceptionGroup):
        exc = ExceptionGroup(str(exc), [remove_tb(subexc) for subexc in exc.exceptions])

    exc.__traceback__ = None

    return exc


@mutable
class ThermiteExcHandler:
    show_tb: bool = False

    def __call__(self, exc: Exception):
        if isinstance(exc, ThermiteException):
            if not self.show_tb:
                exc = remove_tb(exc)
            tb_exc = traceback.TracebackException.from_exception(exc)
            console.print("".join(list(tb_exc.format())))
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
