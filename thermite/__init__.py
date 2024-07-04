"""A package for easily creating CLIs."""
__version__ = "0.1.1"

from .command import CliCallback
from .config import Config, EventCallback
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
    "EventCallback",
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
