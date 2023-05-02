import inspect
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

from attrs import field, mutable
from docstring_parser import Docstring, parse

from thermite.config import Event, EventCallbacks, standardize_obj


class CliParamKind(Enum):
    OPTION = "OPTION"
    ARGUMENT = "ARGUMENT"


@mutable
class ParameterSignature:
    name: str
    python_kind: inspect._ParameterKind
    cli_kind: CliParamKind
    descr: Optional[str]
    default_value: Any
    annot: Type

    def __attrs_post_init__(self):
        # get default value
        if self.default_value == inspect.Parameter.empty:
            self.default_value = ...

        if self.annot == inspect.Parameter.empty:
            self.annot = str


@mutable
class ObjSignature:
    short_descr: Optional[str]
    long_descr: Optional[str]
    params: Dict[str, ParameterSignature]
    return_annot: Type


@mutable(kw_only=True)
class Descriptions:
    short_descr: Optional[str] = None
    long_descr: Optional[str] = None
    args_doc_dict: Dict[str, Optional[str]] = field(
        factory=lambda: defaultdict(lambda: None)
    )

    def update(self, obj: Any):
        obj_doc = inspect.getdoc(obj)
        if obj_doc is not None:
            obj_doc_parsed = parse(obj_doc)
            if obj_doc_parsed.long_description is not None:
                self.long_descr = obj_doc_parsed.long_description
            if obj_doc_parsed.short_description is not None:
                self.short_descr = obj_doc_parsed.short_description
            self.args_doc_dict.update(
                {x.arg_name: x.description for x in obj_doc_parsed.params}
            )


def doc_to_dict(doc_parsed: Docstring) -> Dict[str, Optional[str]]:
    res: Dict[str, Optional[str]] = defaultdict(lambda: None)
    res.update({x.arg_name: x.description for x in doc_parsed.params})
    return res


def extract_descriptions(obj: Any) -> Descriptions:
    descr = Descriptions()
    if inspect.isclass(obj):
        # for a class, we first grab init, and then overwrite with the
        # docs of the class itself so that the class docs have precendence
        descr.update(obj.__init__)
        descr.update(obj)
    else:
        descr.update(obj)

    return descr


def create_params_sig_dict(
    func_sig_params, args_doc_dict
) -> Dict[str, ParameterSignature]:
    params = {}
    for name, param in func_sig_params.items():
        params[name] = ParameterSignature(
            name=name,
            python_kind=param.kind,
            cli_kind=CliParamKind.OPTION,
            descr=args_doc_dict[name],
            default_value=param.default,
            annot=param.annotation,
        )

    return params


def process_function_to_obj_signature(func: Callable) -> ObjSignature:
    descriptions = extract_descriptions(func)
    func_sig = inspect.signature(func)

    return ObjSignature(
        params=create_params_sig_dict(func_sig.parameters, descriptions.args_doc_dict),
        return_annot=func_sig.return_annotation,
        short_descr=descriptions.short_descr,
        long_descr=descriptions.long_descr,
    )


def process_class_to_obj_signature(klass: Type) -> ObjSignature:
    descriptions = extract_descriptions(klass)
    if klass.__init__ != object.__init__:
        init_sig = inspect.signature(klass.__init__)
        return ObjSignature(
            params=create_params_sig_dict(
                init_sig.parameters, descriptions.args_doc_dict
            ),
            return_annot=klass,
            short_descr=descriptions.short_descr,
            long_descr=descriptions.long_descr,
        )

    else:
        return process_instance_to_obj_signature(klass())


def process_instance_to_obj_signature(obj: Any) -> ObjSignature:
    # get the documentation
    klass_doc = inspect.getdoc(obj.__class__)

    if klass_doc is not None:
        klass_doc_parsed = parse(klass_doc)
        short_descr = klass_doc_parsed.short_description
        long_descr = klass_doc_parsed.long_description
    else:
        short_descr = None
        long_descr = None

    # as it is an instance, there are no things to call
    return ObjSignature(
        params={},
        return_annot=obj.__class__,
        short_descr=short_descr,
        long_descr=long_descr,
    )


def match_obj_filter_sig(
    obj_to_match: Any, cb: Callable[[Any, "ObjSignature"], "ObjSignature"]
) -> Callable[[Any, "ObjSignature"], "ObjSignature"]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(obj: Any, sig: "ObjSignature") -> "ObjSignature":
        if standardize_obj(obj) == std_obj_to_match:
            return cb(obj, sig)
        else:
            return sig

    return filtered_callback


EventCallbacks.default_event_obj_filters[Event.SIG_EXTRACT] = match_obj_filter_sig
