import inspect
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from attrs import field, mutable
from beartype.door import is_bearable

from thermite.exceptions import (
    DuplicatedTriggerError,
    UnexpectedReturnTypeError,
    UnexpectedTriggerError,
    UnspecifiedObjError,
)
from thermite.help import OptionGroupHelp
from thermite.utils import split_args_by_nargs

from .base import Argument, Option, Parameter

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class ParameterGroup:
    descr: Optional[str] = None
    obj: Any = None
    _expected_ret_type: object = None
    _posargs: List[Union[Parameter, "ParameterGroup"]] = field(factory=list)
    _varposargs: List[Union[Parameter, "ParameterGroup"]] = field(factory=list)
    _kwargs: Dict[str, Union[Parameter, "ParameterGroup"]] = field(factory=dict)
    _num_bound: int = field(default=0, init=False)
    _prefix: str = ""
    _name: str = ""
    default_value: Any = field(default=...)

    def _exec_obj(self) -> Any:
        if self.obj is None:
            raise UnspecifiedObjError()
        if inspect.isfunction(self.obj):
            res_obj = self.obj(*self.args_values, **self.kwargs_values)
            if not is_bearable(res_obj, self._expected_ret_type):
                raise UnexpectedReturnTypeError(
                    f"Expected return type {str(self._expected_ret_type)} "
                    f"but got {str(type(res_obj))}"
                )
        elif inspect.isclass(self.obj):
            res_obj = self.obj(*self.args_values, **self.kwargs_values)
        else:
            raise NotImplementedError()

        return res_obj

    def _set_prefix_children(self):
        for opt in self.cli_opts:
            opt.prefix = self.child_prefix

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str):
        self._prefix = prefix
        self._set_prefix_children()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self._set_prefix_children()

    @property
    def child_prefix(self) -> str:
        if self.prefix != "":
            return f"{self.prefix}-{self.name}"
        else:
            return self.name

    def bind(self, input_args: Sequence[str]) -> Optional[Sequence[str]]:
        if len(input_args) == 0:
            return []

        if input_args[0].startswith("-"):
            opts_by_trigger = self.final_trigger_mappings
            if input_args[0] in opts_by_trigger:
                self._num_bound += 1
                opt = opts_by_trigger[input_args[0]]
                args_use, args_remain = split_args_by_nargs(input_args, opt.nargs)
                bind_res = opt.bind(args_use)

                # put together return; bind_res of None has special meaning
                if len(args_remain) == 0:
                    if bind_res is None:
                        return None
                    else:
                        return bind_res
                else:
                    if bind_res is None:
                        return args_remain
                    else:
                        return bind_res + args_remain
            else:
                raise UnexpectedTriggerError(f"No option with trigger {input_args[0]}")

        else:
            for argument in self.cli_args:
                if argument.unset:
                    args_use, args_remain = split_args_by_nargs(
                        input_args, argument.nargs
                    )
                    argument.bind(args_use)
                    return args_remain

        return input_args

    @property
    def args_values(self) -> Tuple[Any, ...]:
        res = [x.value for x in self._posargs]
        for arg in self._varposargs:
            res.extend(arg.value)

        return tuple(res)

    @property
    def kwargs_values(self) -> Dict[str, Any]:
        return {key: arg.value for key, arg in self._kwargs.items()}

    @property
    def value(self) -> Any:
        return self._exec_obj()

    @property
    def cli_args(self) -> List[Argument]:
        posargs_args = [x for x in self._posargs if isinstance(x, Argument)]
        varposarg_args = [x for x in self._varposargs if isinstance(x, Argument)]
        kwargs_args = [x for x in self._kwargs.values() if isinstance(x, Argument)]
        return posargs_args + varposarg_args + kwargs_args

    @property
    def cli_opts(self) -> List[Union[Option, "ParameterGroup"]]:
        posargs_opts = [
            x for x in self._posargs if isinstance(x, (Option, ParameterGroup))
        ]
        varposarg_opts = [
            x for x in self._varposargs if isinstance(x, (Option, ParameterGroup))
        ]
        kwargs_opts = [
            x for x in self._kwargs.values() if isinstance(x, (Option, ParameterGroup))
        ]
        return posargs_opts + varposarg_opts + kwargs_opts

    @property
    def final_trigger_mappings(self) -> Dict[str, Option]:
        all_trigger_mappings: Dict[str, Option] = {}
        for opt in self.cli_opts:
            for trigger, trigger_opt in opt.final_trigger_mappings.items():
                if trigger in all_trigger_mappings:
                    raise DuplicatedTriggerError(
                        f"Trigger {trigger} is in options {trigger_opt} "
                        f"and {all_trigger_mappings[trigger]}"
                    )
                else:
                    all_trigger_mappings[trigger] = trigger_opt
        return all_trigger_mappings

    def help_opts_only(self) -> OptionGroupHelp:
        cli_opts = self.cli_opts

        cli_opts_single = [x for x in cli_opts if isinstance(x, Option)]
        cli_opts_group = [x for x in cli_opts if isinstance(x, ParameterGroup)]

        return OptionGroupHelp(
            name=self.name,
            descr=self.descr,
            gen_opts=[x.help() for x in cli_opts_single],
            opt_groups=[x.help_opts_only() for x in cli_opts_group],
        )


@mutable(slots=False, kw_only=True)
class NoOpGroup:
    descr: Optional[str] = None
    obj: Any = None
