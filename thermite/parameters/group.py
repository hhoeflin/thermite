import inspect
from collections.abc import MutableMapping
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from attrs import field, mutable
from beartype.door import is_bearable
from typing_extensions import assert_never

from thermite.exceptions import (
    DuplicatedTriggerError,
    MultiParameterError,
    ParameterError,
    TriggerError,
)
from thermite.help import OptionGroupHelp
from thermite.utils import split_args_by_nargs

from .base import Argument, Option, Parameter

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class ParameterGroup(MutableMapping):
    descr: Optional[str] = None
    obj: Any = None
    default_value: Any = field(default=...)
    _expected_ret_type: object = None
    _posargs: List[Union[Parameter, "ParameterGroup"]]
    _varposargs: List[Union[Parameter, "ParameterGroup"]]
    _kwargs: Dict[str, Union[Parameter, "ParameterGroup"]]
    _prefix: str = ""
    _name: str = ""
    _num_bound: int = field(default=0, init=False)
    _child_prefix_omit_name: bool = True

    def __attrs_post_init__(self):
        self._set_prefix_children()
        if self._expected_ret_type == inspect._empty:
            self._expected_ret_type = type(None)

    def __getitem__(self, key) -> Union[Parameter, "ParameterGroup"]:
        for param in self._posargs:
            if param.name == key:
                return param

        for param in self._varposargs:
            if param.name == key:
                return param

        if key in self._kwargs:
            return self._kwargs[key]

        raise KeyError(f"Parameter with name {key} not found.")

    def __setitem__(self, key, value):
        if not isinstance(value, Parameter) or isinstance(value, ParameterGroup):
            raise ValueError("Can only set object of type Parameter or ParameterGroup")

        if not value.name == key:
            raise ValueError(
                "The name of the parameter being set has to be equal to the key"
            )

        for i, param in enumerate(self._posargs):
            if key == param.name:
                self._posargs[i] = value
                return

        for i, param in enumerate(self._varposargs):
            if key == param.name:
                self._varposargs[i] = value
                return

        if key in self._kwargs:
            self._kwargs[key] = value
            return

        raise KeyError(f"Parameter with name {key} not found.")

    def __delitem__(self, key):
        del key
        raise Exception("Deleting of paraeters not possible.")

    def __len__(self) -> int:
        return len(self._posargs) + len(self._varposargs) + len(self._kwargs)

    def __iter__(self):
        for param in self._posargs:
            yield param.name

        for param in self._varposargs:
            yield param.name

        yield from self._kwargs

    def _exec_obj(self) -> Any:
        if self.obj is None:
            raise ParameterError(f"No object specified in ParameterGroup {self._name}")

        # check if all the input parameters are ok
        args = self.args_values_with_excs
        kwargs = self.kwargs_values_with_excs
        caught_errors = [x for x in args if isinstance(x, ParameterError)] + [
            v for v in kwargs.values() if isinstance(v, ParameterError)
        ]

        if len(caught_errors) > 0:
            raise MultiParameterError(
                f"Caught {len(caught_errors)} in parameters of ParameterGroup '{self._name}'",
                caught_errors,
            )

        if inspect.isfunction(self.obj) or inspect.ismethod(self.obj):
            try:
                res_obj = self.obj(*self.args_values, **self.kwargs_values)
            except Exception as e:
                raise ParameterError(
                    f"Error processing object in ParameterGroup {self._name}"
                ) from e
            if not is_bearable(res_obj, self._expected_ret_type):
                raise ParameterError(
                    f"Expected return type {str(self._expected_ret_type)} "
                    f"but got {str(type(res_obj))} in ParameterGroup '{self._name}'"
                )
        elif inspect.isclass(self.obj):
            try:
                res_obj = self.obj(*self.args_values, **self.kwargs_values)
            except Exception as e:
                raise ParameterError(
                    f"Error processing object in ParameterGroup {self._name}"
                ) from e
        else:
            raise NotImplementedError()

        return res_obj

    @property
    def child_prefix(self) -> str:
        # note that child prefix depends on
        # - prefix
        # - name
        # - child_prefix_omit_name
        # If any of these changes, it should be reset
        prefixes = []
        if self.prefix != "":
            prefixes.append(self.prefix)

        if not self.child_prefix_omit_name and self.name != "":
            prefixes.append(self.name)

        return "-".join(prefixes)

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
    def child_prefix_omit_name(self) -> bool:
        return self._child_prefix_omit_name

    @child_prefix_omit_name.setter
    def child_prefix_omit_name(self, child_prefix_omit_name: bool):
        self._child_prefix_omit_name = child_prefix_omit_name
        self._set_prefix_children()

    def process(self, input_args: Sequence[str]) -> Sequence[str]:
        if len(input_args) == 0:
            return []

        if input_args[0].startswith("-"):
            opts_by_trigger = self.final_trigger_map
            if input_args[0] in opts_by_trigger:
                self._num_bound += 1
                opt = opts_by_trigger[input_args[0]]
                bind_res = opt.process(input_args)

                return bind_res
            else:
                raise TriggerError(f"No option with trigger {input_args[0]}")

        else:
            for argument in self.cli_args:
                if argument.unset:
                    self._num_bound += 1
                    args_use, args_remain = split_args_by_nargs(
                        input_args, argument.nargs
                    )
                    argument.process(args_use)
                    return args_remain

        return input_args

    def _num_params(self) -> int:
        return len(self._posargs) + len(self._varposargs) + len(self._kwargs)

    @property
    def args_values(self) -> Tuple[Any, ...]:
        res = [x.value for x in self._posargs]
        for arg in self._varposargs:
            res.extend(arg.value)

        return tuple(res)

    @property
    def args_values_with_excs(self) -> Tuple[Any, ...]:
        res = []
        for x in self._posargs:
            try:
                res.append(x.value)
            except Exception as e:
                res.append(e)
        for arg in self._varposargs:
            try:
                res.extend(arg.value)
            except Exception as e:
                res.append(e)

        return tuple(res)

    @property
    def kwargs_values(self) -> Dict[str, Any]:
        return {key: arg.value for key, arg in self._kwargs.items()}

    @property
    def kwargs_values_with_excs(self) -> Dict[str, Any]:
        res = {}
        for key, arg in self._kwargs.items():
            try:
                res[key] = arg.value
            except Exception as e:
                res[key] = e
        return res

    @property
    def unset(self) -> bool:
        return self._num_bound == 0

    @property
    def is_required(self) -> bool:
        return self.default_value == ... and self._num_params() > 0

    @property
    def value(self) -> Any:
        try:
            if self._num_params() == 0 or not self.unset or self.default_value == ...:
                return self._exec_obj()
            else:
                return self.default_value
        except ParameterError:
            raise
        except Exception as e:
            raise ParameterError(f"Error in ParameterGroup '{self._name}'") from e

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
    def final_trigger_map(self) -> Dict[str, Union[Option, "ParameterGroup"]]:
        all_trigger_mappings: Dict[str, Union[Option, "ParameterGroup"]] = {}
        for opt in self.cli_opts:
            if isinstance(opt, Option):
                for trigger in opt.final_triggers:
                    if trigger in all_trigger_mappings:
                        raise DuplicatedTriggerError(
                            f"Trigger {trigger} option {opt} "
                            f"and {all_trigger_mappings[trigger]}"
                        )
                    else:
                        all_trigger_mappings[trigger] = opt
            elif isinstance(opt, ParameterGroup):
                for trigger, trigger_opt in opt.final_trigger_map.items():
                    if trigger in all_trigger_mappings:
                        raise DuplicatedTriggerError(
                            f"Trigger {trigger} is in options {trigger_opt} "
                            f"and {all_trigger_mappings[trigger]}"
                        )
                    else:
                        all_trigger_mappings[trigger] = opt
            else:
                assert_never(opt)

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
