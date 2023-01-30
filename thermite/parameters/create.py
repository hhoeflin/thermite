import inspect
from collections import defaultdict
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    get_args,
    get_origin,
)

from docstring_parser import Docstring, parse

from thermite.type_converters import CLIArgConverterStore
from thermite.utils import clify_argname

from .base import BoolOption, KnownLenArg, KnownLenOpt, Parameter
from .group import ParameterGroup


def process_parameter(
    param: inspect.Parameter,
    description: Optional[str],
    store: CLIArgConverterStore,
) -> Union[Parameter, ParameterGroup]:
    """
    Process a function parameter into a thermite parameter
    """
    # find the right type converter
    # if no type annotations, it is assumed it is str
    if param.annotation != inspect.Parameter.empty:
        annot_to_use: Type = param.annotation
    else:
        annot_to_use = str

    # get default value
    if param.default == inspect.Parameter.empty:
        default_val = ...
    else:
        default_val = param.default

    # extract docs for this parameter

    # check if is should be an argument or an option
    if param.kind == inspect.Parameter.POSITIONAL_ONLY:
        conv = store.get_converter(annot_to_use)
        # single argument
        return KnownLenArg(
            name=param.name,
            descr=description,
            default_value=default_val,
            type_converter=conv,
            target_type_str=str(annot_to_use),
            callback=None,
        )
    elif param.kind == inspect.Parameter.VAR_POSITIONAL:
        # argument list
        # the converter needs to be changed; the type annotation is per item,
        # not for the whole list
        annot_to_use = List[annot_to_use]  # type: ignore
        conv = store.get_converter(annot_to_use)
        return KnownLenArg(
            name=param.name,
            descr=description,
            default_value=default_val,
            type_converter=conv,
            target_type_str=str(annot_to_use),
            callback=None,
        )
    elif param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        if annot_to_use == bool:
            # need to use a bool-option
            return BoolOption(
                name=param.name,
                default_value=default_val,
                descr=description,
                pos_triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                neg_triggers=[f"--no-{clify_argname(param.name)}"],  # type: ignore
            )
        elif get_origin(annot_to_use) in (List, Sequence):
            annot_args = get_args(annot_to_use)
            if len(annot_args) == 0:
                inner_type = str
            elif len(annot_args) == 1:
                inner_type = annot_args[0]
            else:
                raise TypeError(f"{str(annot_to_use)} has more than 1 argument.")

            conv = store.get_converter(inner_type)
            return KnownLenOpt(
                name=param.name,
                descr=description,
                default_value=default_val,
                type_converter=conv,
                target_type_str=str(annot_to_use),
                triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                multiple=True,
            )
        else:
            try:
                conv = store.get_converter(annot_to_use)
                return KnownLenOpt(
                    name=param.name,
                    descr=description,
                    default_value=default_val,
                    target_type_str=str(annot_to_use),
                    type_converter=conv,
                    triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                    multiple=False,
                )
            except TypeError:
                # see if this could be done using a class option group
                if inspect.isclass(annot_to_use):
                    res = process_class_to_param_group(
                        klass=annot_to_use,
                        store=store,
                    )
                    res.name = param.name
                    return res
                else:
                    raise
    elif param.kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param.kind}")


def doc_to_dict(doc_parsed: Docstring) -> Dict[str, Optional[str]]:
    res: Dict[str, Optional[str]] = defaultdict(lambda: None)
    res.update({x.arg_name: x.description for x in doc_parsed.params})
    return res


def process_function_to_param_group(
    func: Callable, store: CLIArgConverterStore
) -> ParameterGroup:
    func_sig = inspect.signature(func)

    # preprocess the documentation
    func_doc = inspect.getdoc(func)
    if func_doc is not None:
        doc_parsed = parse(func_doc)
        short_description = doc_parsed.short_description
        args_doc_dict = doc_to_dict(doc_parsed)
    else:
        short_description = None
        args_doc_dict = defaultdict(lambda: None)

    param_group = ParameterGroup(
        descr=short_description,
        obj=func,
        expected_ret_type=func_sig.return_annotation,
    )
    for param in func_sig.parameters.values():
        cli_param = process_parameter(
            param=param,
            description=args_doc_dict[param.name],
            store=store,
        )
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            param_group.posargs.append(cli_param)
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            param_group.varposargs.append(cli_param)
        else:
            param_group.kwargs[param.name] = cli_param

    return param_group


def process_class_to_param_group(
    klass: Type,
    store: CLIArgConverterStore,
) -> ParameterGroup:
    init_sig = inspect.signature(klass.__init__)

    # get the documentation
    klass_doc = inspect.getdoc(klass)
    init_doc = inspect.getdoc(klass.__init__)
    if klass_doc is not None:
        klass_doc_parsed = parse(klass_doc)
        short_description = klass_doc_parsed.short_description
    else:
        short_description = None

    if init_doc is not None:
        init_doc_parsed = parse(init_doc)
        args_doc_dict = doc_to_dict(init_doc_parsed)
    else:
        args_doc_dict = defaultdict(lambda: None)

    # the signature has self at the beginning that we need to ignore
    param_group = ParameterGroup(
        descr=short_description, obj=klass, expected_ret_type=klass
    )
    for count, param in enumerate(init_sig.parameters.values()):
        if count == 0:
            # this is self
            continue
        else:
            cli_param = process_parameter(
                param=param,
                description=args_doc_dict[param.name],
                store=store,
            )
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                param_group.posargs.append(cli_param)
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                param_group.varposargs.append(cli_param)
            else:
                param_group.kwargs[param.name] = cli_param

    return param_group
