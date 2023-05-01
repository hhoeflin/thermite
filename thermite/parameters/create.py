import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from attrs import asdict

from thermite.config import Config, Event
from thermite.signatures import (
    CliParamKind,
    ObjSignature,
    ParameterSignature,
    process_class_to_obj_signature,
    process_function_to_obj_signature,
    process_instance_to_obj_signature,
)
from thermite.utils import clean_type_str, clify_argname

from .base import Option, Parameter
from .group import ParameterGroup
from .processors import (
    ConstantTriggerProcessor,
    ConvertListTriggerProcessor,
    ConvertReplaceTriggerProcessor,
)


def process_parameter(
    param_sig: ParameterSignature, config: Config
) -> Union[Parameter, ParameterGroup]:
    """
    Process a function parameter into a thermite parameter
    """
    # find the right type converter
    # if no type annotations, it is assumed it is str
    store = config.cli_args_store
    res: Union[Parameter, ParameterGroup]

    if param_sig.python_kind == inspect.Parameter.VAR_POSITIONAL:
        # argument list
        # the converter needs to be changed; the type annotation is per item,
        # not for the whole list
        annot_to_use = List[param_sig.annot]  # type: ignore
        conv = store.get_converter(annot_to_use)
        res = Option(
            **asdict(param_sig),
            processors=[
                ConvertListTriggerProcessor(
                    triggers=[f"--{clify_argname(param_sig.name)}"],
                    type_converter=conv,
                    type_str=clean_type_str(annot_to_use),
                )
            ],
        )
    elif param_sig.python_kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_ONLY,
    ):
        if param_sig.annot == bool:
            # need to use a bool-option
            res = bool_option(
                param_sig=param_sig,
                pos_triggers=[f"--{clify_argname(param_sig.name)}"],
                neg_triggers=[f"--no-{clify_argname(param_sig.name)}"],
            )
        elif get_origin(param_sig.annot) in (List, list, Sequence):
            annot_args = get_args(param_sig.annot)
            if len(annot_args) == 0:
                inner_type = str
            elif len(annot_args) == 1:
                inner_type = annot_args[0]
            else:
                raise TypeError(f"{str(param_sig.annot)} has more than 1 argument.")
            conv = store.get_converter(inner_type)
            res = Option(
                **asdict(param_sig),
                processors=[
                    ConvertListTriggerProcessor(
                        triggers=[f"--{clify_argname(param_sig.name)}"],
                        type_converter=conv,
                        type_str=clean_type_str(param_sig.annot),
                    )
                ],
            )
        else:
            try:
                conv = store.get_converter(param_sig.annot)
                res = Option(
                    **asdict(param_sig),
                    processors=[
                        ConvertReplaceTriggerProcessor(
                            triggers=[f"--{clify_argname(param_sig.name)}"],
                            type_converter=conv,
                            type_str=clean_type_str(param_sig.annot),
                        )
                    ],
                )
            except TypeError:
                # see if this could be done using a class option group
                if inspect.isclass(param_sig.annot):
                    res = process_class_to_param_group(
                        klass=param_sig.annot,
                        config=config,
                        name=param_sig.name,
                        child_prefix_omit_name=False,
                    )
                    res.default_value = param_sig.default_value
                else:
                    raise
    elif param_sig.python_kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param_sig.python_kind}")

    if param_sig.cli_kind == CliParamKind.ARGUMENT:
        if isinstance(res, Option):
            res = res.to_argument()
        elif isinstance(res, ParameterGroup):
            raise Exception("Can't convert ParamGroup to Argument")

    return res


def bool_option(
    param_sig: ParameterSignature,
    pos_triggers: Sequence[str],
    neg_triggers: Sequence[str],
    prefix: str = "",
):
    return Option(
        **asdict(param_sig),
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


def process_param_sig_dict(
    params: Dict[str, ParameterSignature],
    omit_first: bool,
    config: Config,
) -> Tuple[
    List[Union[Parameter, ParameterGroup]],
    List[Union[Parameter, ParameterGroup]],
    Dict[str, Union[Parameter, ParameterGroup]],
]:
    posargs = []
    varposargs = []
    kwargs = {}
    for count, param in enumerate(params.values()):
        if omit_first and count == 0:
            # this is self
            continue
        else:
            if param.python_kind == inspect.Parameter.VAR_KEYWORD:
                continue
            else:
                cli_param = process_parameter(
                    param_sig=param,
                    config=config,
                )
                if param.python_kind == inspect.Parameter.POSITIONAL_ONLY:
                    posargs.append(cli_param)
                elif param.python_kind == inspect.Parameter.VAR_POSITIONAL:
                    varposargs.append(cli_param)
                else:
                    kwargs[param.name] = cli_param

    return (posargs, varposargs, kwargs)


def process_obj_signature_to_param_group(
    obj: Any,
    obj_sig: ObjSignature,
    config: Config,
    name: str,
    child_prefix_omit_name: bool,
    omit_first: bool,
) -> ParameterGroup:
    posargs, varposargs, kwargs = process_param_sig_dict(
        obj_sig.params,
        omit_first=omit_first,
        config=config,
    )
    param_group = ParameterGroup(
        descr=obj_sig.short_descr,
        obj=obj,
        expected_ret_type=obj_sig.return_annot,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        posargs=posargs,
        varposargs=varposargs,
        kwargs=kwargs,
    )

    return param_group


def process_function_to_param_group(
    func: Callable, config: Config, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    obj_sig = process_function_to_obj_signature(func=func)
    # SIG_EXTRACT Event start
    for cb in config.get_event_cbs(Event.SIG_EXTRACT):
        obj_sig = cb(func, obj_sig)
    # SIG_EXTRACT Event end
    pg = process_obj_signature_to_param_group(
        obj=func,
        obj_sig=obj_sig,
        config=config,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        omit_first=False,
    )
    # PG_POST_CREATE Event start
    for cb in config.get_event_cbs(Event.PG_POST_CREATE):
        pg = cb(pg)
    # PG_POST_CREATE Event end
    return pg


def process_class_to_param_group(
    klass: Type, config: Config, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    obj_sig = process_class_to_obj_signature(klass=klass)
    # SIG_EXTRACT Event start
    for cb in config.get_event_cbs(Event.SIG_EXTRACT):
        obj_sig = cb(klass, obj_sig)
    # SIG_EXTRACT Event end
    pg = process_obj_signature_to_param_group(
        obj=klass,
        obj_sig=obj_sig,
        config=config,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        omit_first=True,
    )
    # PG_POST_CREATE Event start
    for cb in config.get_event_cbs(Event.PG_POST_CREATE):
        pg = cb(pg)
    # PG_POST_CREATE Event end
    return pg


def process_instance_to_param_group(
    obj: Any, config: Config, name: str, child_prefix_omit_name: bool
) -> ParameterGroup:
    obj_sig = process_instance_to_obj_signature(obj=obj)
    # SIG_EXTRACT Event start
    for cb in config.get_event_cbs(Event.SIG_EXTRACT):
        obj_sig = cb(obj, obj_sig)
    # SIG_EXTRACT Event end
    pg = process_obj_signature_to_param_group(
        obj=lambda: obj,
        obj_sig=obj_sig,
        config=config,
        name=name,
        child_prefix_omit_name=child_prefix_omit_name,
        omit_first=False,
    )
    # PG_POST_CREATE Event start
    for cb in config.get_event_cbs(Event.PG_POST_CREATE):
        pg = cb(pg)
    # PG_POST_CREATE Event end
    return pg
