import inspect
from typing import Callable, List, Sequence, Type, Union, get_args, get_origin

from thermite.type_converters import ComplexTypeConverterFactory
from thermite.utils import clify_argname

from .base import BoolOption, KnownLenArg, KnownLenOpt, NoOpOption, Parameter
from .group import ParameterGroup


def process_parameter(
    param: inspect.Parameter,
    description: str,
    complex_factory: ComplexTypeConverterFactory,
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
        conv_nargs = complex_factory.converter_factory(annot_to_use)
        # single argument
        return KnownLenArg(
            descr=description,
            nargs=conv_nargs.nargs,
            value=default_val,
            type_converter=conv_nargs.converter,
            callback=None,
        )
    elif param.kind == inspect.Parameter.VAR_POSITIONAL:
        # argument list
        # the converter needs to be changed; the type annotation is per item,
        # not for the whole list
        annot_to_use = List[annot_to_use]  # type: ignore
        conv_nargs = complex_factory.converter_factory(annot_to_use)
        return KnownLenArg(
            descr=description,
            nargs=conv_nargs.nargs,
            value=default_val,
            type_converter=conv_nargs.converter,
            callback=None,
        )
    elif param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        if annot_to_use == bool:
            # need to use a bool-option
            return BoolOption(
                value=default_val,
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

            conv_nargs = complex_factory.converter_factory(inner_type)
            return KnownLenOpt(
                descr=description,
                value=default_val,
                nargs=conv_nargs.nargs,
                type_converter=conv_nargs.converter,
                triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                multiple=True,
            )
        else:
            try:
                conv_nargs = complex_factory.converter_factory(annot_to_use)
                return KnownLenOpt(
                    descr=description,
                    value=default_val,
                    nargs=conv_nargs.nargs,
                    type_converter=conv_nargs.converter,
                    triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                    multiple=False,
                )
            except TypeError:
                # see if this could be done using a class option group
                if inspect.isclass(annot_to_use):
                    return process_class_to_param_group(
                        klass=annot_to_use,
                        complex_factory=complex_factory,
                    )
            raise NotImplementedError()

    elif param.kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param.kind}")


def process_function_to_param_group(
    func: Callable, complex_factory: ComplexTypeConverterFactory
) -> ParameterGroup:
    func_sig = inspect.signature(func)

    param_group = ParameterGroup(
        descr="",
        obj=func,
        expected_ret_type=func_sig.return_annotation,
    )
    for param in func_sig.parameters.values():
        cli_param = process_parameter(
            param=param, description="", complex_factory=complex_factory
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
    complex_factory: ComplexTypeConverterFactory,
) -> ParameterGroup:
    init_sig = inspect.signature(klass.__init__)

    # the signature has self at the beginning that we need to ignore
    param_group = ParameterGroup(descr="", obj=klass, expected_ret_type=klass)
    for count, param in enumerate(init_sig.parameters.values()):
        if count == 0:
            # this is self
            continue
        else:
            cli_param = process_parameter(
                param=param, description="", complex_factory=complex_factory
            )
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                param_group.posargs.append(cli_param)
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                param_group.varposargs.append(cli_param)
            else:
                param_group.kwargs[param.name] = cli_param

    return param_group
