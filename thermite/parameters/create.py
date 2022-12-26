import inspect
from typing import List, Sequence, Type, get_args, get_origin

from thermite.type_converters import ComplexTypeConverterFactory
from thermite.utils import clify_argname

from .base import BoolOption, KnownLenArg, KnownLenOpt, NoOpOption, Parameter


def process_parameter(
    param: inspect.Parameter,
    description: str,
    complex_factory: ComplexTypeConverterFactory,
) -> Parameter:
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
                    # it is a class that we want to use
                    raise NotImplementedError
            raise NotImplementedError()

    elif param.kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param.kind}")
