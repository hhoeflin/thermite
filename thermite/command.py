import inspect
from inspect import Signature
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Sequence,
    Type,
    get_args,
    get_origin,
)

from attrs import mutable
from beartype.door import is_bearable

from .exceptions import (
    NothingProcessedError,
    UnexpectedReturnTypeError,
    UnprocessedArgumentError,
)
from .parameters import BoolOption, KnownLenArg, KnownLenOpt, Parameter, ParameterGroup
from .preprocessing import split_and_expand
from .type_converters import ComplexTypeConverterFactory
from .utils import clify_argname


def extract_subcommands(return_type: Any) -> Dict[str, Any]:
    if return_type == Signature.empty:
        return {}
    else:
        return {}


@mutable(slots=False)
class Command:
    obj: Any
    param_group: ParameterGroup
    expected_ret_type: object
    subcommand_objs: Dict[str, Any]

    _complex_factory: ClassVar[
        ComplexTypeConverterFactory
    ] = ComplexTypeConverterFactory()

    @classmethod
    def _from_function(cls, func: Callable):
        func_sig = inspect.signature(func)

        param_group = ParameterGroup(descr="")
        for param in func_sig.parameters.values():
            param_group.add_param(
                name=param.name,
                param=process_parameter(
                    param=param, description="", complex_factory=cls._complex_factory
                ),
            )

        return cls(
            obj=func,
            param_group=param_group,
            expected_ret_type=func_sig.return_annotation,
            subcommand_objs={},
        )

    @classmethod
    def _from_class(cls, klass: Type):
        init_sig = inspect.signature(klass.__init__)

        # the signature has self at the beginning that we need to ignore
        param_group = ParameterGroup(descr="")
        for count, param in enumerate(init_sig.parameters.values()):
            if count == 0:
                # this is self
                continue
            else:
                param_group.add_param(
                    name=param.name,
                    param=process_parameter(
                        param=param,
                        description="",
                        complex_factory=cls._complex_factory,
                    ),
                )

        return cls(
            obj=klass,
            param_group=param_group,
            expected_ret_type=klass,
            subcommand_objs={},
        )

    @classmethod
    def from_obj(cls, obj: Any):
        if inspect.isfunction(obj):
            return cls._from_function(func=obj)
        elif inspect.isclass(obj):
            return cls._from_class(obj)
        else:
            raise NotImplementedError()

    def _exec_command(self) -> Any:
        if inspect.isfunction(self.obj):
            res_obj = self.obj(*self.param_group.args, **self.param_group.kwargs)
            if not is_bearable(res_obj, self.expected_ret_type):
                raise UnexpectedReturnTypeError(
                    f"Expected return type {str(self.expected_ret_type)} "
                    f"but got {str(type(res_obj))}"
                )
        elif inspect.isclass(self.obj):
            res_obj = self.obj(*self.param_group.args, **self.param_group.kwargs)
        else:
            raise NotImplementedError()

        return res_obj

    def process_multiple(self, args: Sequence[str]) -> Any:
        input_args_deque = split_and_expand(args)

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()
            try:
                args_return = self.param_group.process(input_args)
            except NothingProcessedError:
                # there are arguments left that the param_group can't handle
                # search through the subcommand_objs
                if input_args[0] in self.subcommand_objs:
                    # get a subcommand, hand all remaining arguments to it
                    input_args_deque.appendleft(input_args[1:])
                    remaining_input_args = list(input_args_deque)
                    input_args_deque.clear()

                    res_obj = self._exec_command()

                    subcommand = self.from_obj(getattr(res_obj, input_args[0]))
                    return subcommand.process_multiple(remaining_input_args)
                else:
                    raise UnprocessedArgumentError(
                        f"Argument {args} could not be processed"
                    )
            if len(args_return) == len(input_args):
                raise Exception("Input args have same length as return args")
            if len(args_return) > 0:
                input_args_deque.appendleft(args_return)

        return self._exec_command()


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
        # option
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
            conv_nargs = complex_factory.converter_factory(annot_to_use)
            return KnownLenOpt(
                descr=description,
                value=default_val,
                nargs=conv_nargs.nargs,
                type_converter=conv_nargs.converter,
                triggers=[f"--{clify_argname(param.name)}"],  # type: ignore
                multiple=False,
            )

    elif param.kind == inspect.Parameter.VAR_KEYWORD:
        # not yet a solution; should allow to pass any option
        raise NotImplementedError("VAR_KEYWORDS not yet supported")
    else:
        raise Exception(f"Unknown value for kind: {param.kind}")
