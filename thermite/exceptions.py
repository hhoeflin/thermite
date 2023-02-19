import sys
from types import ModuleType
from typing import Iterable, Optional, Union

from attrs import asdict, mutable
from rich.text import Text
from rich.traceback import LOCALS_MAX_LENGTH, LOCALS_MAX_STRING, Traceback

from thermite.rich import console


class ThermiteException(Exception):
    pass


class UnexpectedTriggerError(Exception):
    pass


class UnmatchedOriginError(Exception):
    pass


class IncorrectNumberArgs(Exception):
    pass


class DuplicatedTriggerError(Exception):
    pass


class NothingProcessedError(Exception):
    pass


class TooFewInputsError(Exception):
    pass


class UnspecifiedParameterError(ThermiteException):
    pass


class UnspecifiedOptionError(UnspecifiedParameterError):
    pass


class UnspecifiedArgumentError(UnspecifiedParameterError):
    pass


class UnspecifiedObjError(Exception):
    pass


class UnprocessedArgumentError(Exception):
    pass


class UnexpectedReturnTypeError(Exception):
    pass


class UnknownArgumentError(Exception):
    pass


class UnknownOptionError(Exception):
    pass


def thermite_exc_handler(exc: Exception) -> Optional[Exception]:
    if isinstance(exc, ThermiteException):
        console.print(Text(f"{exc.__class__.__name__}: ") + Text(str(exc)))
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
