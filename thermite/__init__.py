"""A package for easily creating CLIs."""
__version__ = "0.1.0"

from .command import CliCallback
from .config import Config, Event
from .parameters import (
    ConstantTriggerProcessor,
    ConvertTriggerProcessor,
    MultiConvertTriggerProcessor,
    Option,
    Parameter,
    ParameterGroup,
)
from .run import run
from .signatures import (
    CliParamKind,
    ObjSignature,
    ParameterSignature,
    process_class_to_obj_signature,
    process_function_to_obj_signature,
    process_instance_to_obj_signature,
)
from .type_converters import BasicCLIArgConverter

__all__ = [
    "run",
    "Config",
    "Event",
    "CliCallback",
    "ObjSignature",
    "ParameterSignature",
    "process_class_to_obj_signature",
    "process_function_to_obj_signature",
    "process_instance_to_obj_signature",
    "CliParamKind",
    "BasicCLIArgConverter",
    "Option",
    "Parameter",
    "ParameterGroup",
    "ConstantTriggerProcessor",
    "ConvertTriggerProcessor",
    "MultiConvertTriggerProcessor",
]
