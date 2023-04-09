import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from docstring_parser import parse
from immutabledict import immutabledict

from thermite.help import extract_descriptions
from thermite.type_converters import CLIArgConverterStore
from thermite.utils import clean_type_str, clify_argname

from .base import Argument, Option, Parameter
from .group import ParameterGroup
from .processors import (
    ConstantTriggerProcessor,
    ConvertListTriggerProcessor,
    ConvertOnceTriggerProcessor,
    ConvertReplaceTriggerProcessor,
)


def bool_option(
    name: str,
    descr: str,
    pos_triggers: Sequence[str],
    neg_triggers: Sequence[str],
    default_value: Any,
    prefix: str = "",
):
    return Option(
        name=name,
        descr=descr,
        default_value=default_value,
        prefix=prefix,
        processors=[
            ConstantTriggerProcessor(
                triggers=pos_triggers, type_str="Bool", constant=True
            ),
            ConstantTriggerProcessor(
                triggers=neg_triggers, type_str="Bool", constant=False
            ),
        ],
    )


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

    if param.kind == inspect.Parameter.VAR_POSITIONAL:
        # argument list
        # the converter needs to be changed; the type annotation is per item,
        # not for the whole list
        annot_to_use = List[annot_to_use]  # type: ignore
        conv = store.get_converter(annot_to_use)
        return Option(
            name=param.name,
            descr=description,
            default_value=default_val,
            processors=[
                ConvertListTriggerProcessor(
                    triggers=[f"--{clify_argname(param.name)}"],
                    type_converter=conv,
                    type_str=clean_type_str(annot_to_use),
                )
            ],
        )
    elif param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_ONLY,
    ):
        if annot_to_use == bool:
            # need to use a bool-option
            return bool_option(
                name=param.name,
                default_value=default_val,
                descr=description if description is not None else "",
                pos_triggers=[f"--{clify_argname(param.name)}"],
                neg_triggers=[f"--no-{clify_argname(param.name)}"],
            )
        elif get_origin(annot_to_use) in (List, list, Sequence):
            annot_args = get_args(annot_to_use)
            if len(annot_args) == 0:
                inner_type = str
            elif len(annot_args) == 1:
                inner_type = annot_args[0]
            else:
                raise TypeError(f"{str(annot_to_use)} has more than 1 argument.")
            conv = store.get_converter(inner_type)
            return Option(
                name=param.name,
                descr=description,
                default_value=default_val,
                processors=[
                    ConvertListTriggerProcessor(
                        triggers=[f"--{clify_argname(param.name)}"],
                        type_converter=conv,
                        type_str=clean_type_str(annot_to_use),
                    )
                ],
            )
        else:
            try:
                conv = store.get_converter(annot_to_use)
                return Option(
                    name=param.name,
                    descr=description,
                    default_value=default_val,
                    processors=[
                        ConvertReplaceTriggerProcessor(
                            triggers=[f"--{clify_argname(param.name)}"],
                            type_converter=conv,
                            type_str=clean_type_str(annot_to_use),
                        )
                    ],
                )
            except TypeError:
                # see if this could be done using a class option group
                if inspect.isclass(annot_to_use):
                    res = process_class_to_param_group(
                        klass=annot_to_use,
                        store=store,
                        name=param.name,
                        child_prefix_omit_name=False,
                    )
                    res.default_value = default_val
                    return res
                else:
                    raise
    elif param.kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param.kind}")


def parse_func_signature(
    params: Sequence[inspect.Parameter],
    args_doc_dict: Dict[str, Optional[str]],
    omit_first: bool,
    store: CLIArgConverterStore,
) -> Tuple[
    List[Union[Parameter, ParameterGroup]],
    List[Union[Parameter, ParameterGroup]],
    Dict[str, Union[Parameter, ParameterGroup]],
]:

    posargs = []
    varposargs = []
    kwargs = {}
    for count, param in enumerate(params):
        if omit_first and count == 0:
            # this is self
            continue
        else:
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            else:
                cli_param = process_parameter(
                    param=param,
                    description=args_doc_dict[param.name],
                    store=store,
                )
                if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    posargs.append(cli_param)
                elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                    varposargs.append(cli_param)
                else:
                    kwargs[param.name] = cli_param

    return (posargs, varposargs, kwargs)


def process_function_to_param_group(
    func: Callable, store: CLIArgConverterStore, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    descriptions = extract_descriptions(func)

    func_sig = inspect.signature(func)

    posargs, varposargs, kwargs = parse_func_signature(
        list(func_sig.parameters.values()),
        args_doc_dict=descriptions.args_doc_dict,
        omit_first=False,
        store=store,
    )
    param_group = ParameterGroup(
        descr=descriptions.short_descr,
        obj=func,
        expected_ret_type=func_sig.return_annotation,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        posargs=posargs,
        varposargs=varposargs,
        kwargs=kwargs,
    )

    return param_group


def process_class_to_param_group(
    klass: Type, store: CLIArgConverterStore, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    descriptions = extract_descriptions(klass)
    if klass.__init__ != object.__init__:
        init_sig = inspect.signature(klass.__init__)

        # the signature has self at the beginning that we need to ignore
        posargs, varposargs, kwargs = parse_func_signature(
            list(init_sig.parameters.values()),
            args_doc_dict=descriptions.args_doc_dict,
            omit_first=True,
            store=store,
        )
        param_group = ParameterGroup(
            descr=descriptions.short_descr,
            obj=klass,
            expected_ret_type=klass,
            name=name,
            child_prefix_omit_name=child_prefix_omit_name,
            posargs=posargs,
            varposargs=varposargs,
            kwargs=kwargs,
        )
        return param_group
    else:
        return process_instance_to_param_group(
            klass(), name=name, child_prefix_omit_name=child_prefix_omit_name
        )


def process_instance_to_param_group(
    obj: Any, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    # get the documentation
    klass_doc = inspect.getdoc(obj.__class__)

    if klass_doc is not None:
        klass_doc_parsed = parse(klass_doc)
        short_description = klass_doc_parsed.short_description
    else:
        short_description = None

    # the signature has self at the beginning that we need to ignore
    param_group = ParameterGroup(
        descr=short_description,
        obj=obj,
        expected_ret_type=obj.__class__,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        posargs=list(),
        varposargs=list(),
        kwargs={},
    )
    return param_group
