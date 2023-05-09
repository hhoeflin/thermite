"""A package for easily creating CLIs."""
__version__ = "0.1.0"

from .command import CliCallback
from .config import Config, Event
from .parameters import Option, Parameter, ParameterGroup
from .run import run
from .signatures import CliParamKind, ObjSignature, ParameterSignature
from .type_converters import BasicCLIArgConverter

__all__ = [
    "run",
    "Config",
    "Event",
    "CliCallback",
    "ObjSignature",
    "ParameterSignature",
    "CliParamKind",
    "BasicCLIArgConverter",
    "Option",
    "Parameter",
    "ParameterGroup",
]
