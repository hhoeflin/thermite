import inspect
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

from attrs import field, mutable
from beartype.door import is_bearable
from typing_extensions import assert_never

from thermite.config import Event, EventCallbacks, standardize_obj
from thermite.exceptions import (
    DuplicatedTriggerError,
    MultiParameterError,
    ParameterError,
    TriggerError,
)
from thermite.signatures import CliParamKind
from thermite.type_converters import split_args_by_nargs

from .base import Argument, Option, Parameter

EllipsisType = type(...)


@mutable(kw_only=True)
class ParameterGroup(MutableMapping):
    name: str = ""
    short_descr: Optional[str] = None
    long_descr: Optional[str] = None
    return_annot: Type
    obj: Any = None
    default_value: Any = field(default=...)
    python_kind: Optional[inspect._ParameterKind]
    params: Dict[str, Union[Parameter, "ParameterGroup"]] = field(factory=dict)
    _prefix_parent: str = ""
    _prefix_this: str = ""
    _num_bound: int = field(default=0, init=False)

    def __attrs_post_init__(self):
        self._set_prefix_children()
        if self.return_annot == inspect._empty:
            self.return_annot = type(None)

    def __getitem__(self, key) -> Union[Parameter, "ParameterGroup"]:
        return self.params[key]

    def __setitem__(self, key, value):
        if not isinstance(value, Parameter) or isinstance(value, ParameterGroup):
            raise ValueError("Can only set object of type Parameter or ParameterGroup")

        if not value.name == key:
            raise ValueError(
                "The name of the parameter being set has to be equal to the key"
            )

        self.params[key] = value

    def __delitem__(self, key):
        del self.params[key]

    def __len__(self) -> int:
        return len(self.params)

    def __iter__(self):
        return self.params.__iter__()

    def _exec_obj(self) -> Any:
        if self.obj is None:
            raise ParameterError(f"No object specified in ParameterGroup {self.name}")

        # check if all the input parameters are ok
        args = self.args_values_with_excs
        kwargs = self.kwargs_values_with_excs
        caught_errors = [x for x in args if isinstance(x, ParameterError)] + [
            v for v in kwargs.values() if isinstance(v, ParameterError)
        ]

        if len(caught_errors) > 0:
            raise MultiParameterError(
                f"Caught {len(caught_errors)} in parameters of ParameterGroup '{self.name}'",
                caught_errors,
            )

        if inspect.isfunction(self.obj) or inspect.ismethod(self.obj):
            try:
                res_obj = self.obj(*self.args_values, **self.kwargs_values)
            except Exception as e:
                raise ParameterError(
                    f"Error processing object in ParameterGroup {self.name}"
                ) from e
            if not is_bearable(res_obj, self.return_annot):
                raise ParameterError(
                    f"Expected return type {str(self.return_annot)} "
                    f"but got {str(type(res_obj))} in ParameterGroup '{self.name}'"
                )
        elif inspect.isclass(self.obj):
            try:
                res_obj = self.obj(*self.args_values, **self.kwargs_values)
            except Exception as e:
                raise ParameterError(
                    f"Error processing object in ParameterGroup {self.name}"
                ) from e
        else:
            raise NotImplementedError()

        return res_obj

    @property
    def posargs(self) -> List[Union[Parameter, "ParameterGroup"]]:
        return [
            p
            for p in self.values()
            if p.python_kind == inspect.Parameter.POSITIONAL_ONLY
        ]

    @property
    def varposargs(self) -> List[Union[Parameter, "ParameterGroup"]]:
        return [
            p
            for p in self.values()
            if p.python_kind == inspect.Parameter.VAR_POSITIONAL
        ]

    @property
    def kwargs(self) -> Dict[str, Union[Parameter, "ParameterGroup"]]:
        return {
            k: p
            for k, p in self.items()
            if p.python_kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }

    @property
    def child_prefix(self) -> str:
        # note that child prefix depends on
        # - prefix
        # - name
        # - child_prefix_omit_name
        # If any of these changes, it should be reset
        prefixes = []
        if self.prefix_parent != "":
            prefixes.append(self.prefix_parent)

        if self.prefix_this != "":
            prefixes.append(self.prefix_this)

        return "-".join(prefixes)

    def _set_prefix_children(self):
        for opt in self.cli_opts:
            if isinstance(opt, ParameterGroup):
                opt.prefix_parent = self.child_prefix
            else:
                opt.prefix = self.child_prefix

    @property
    def prefix_this(self) -> str:
        return self._prefix_this

    @prefix_this.setter
    def prefix_this(self, prefix_this: str):
        self._prefix_this = prefix_this
        self._set_prefix_children()

    @property
    def prefix_parent(self) -> str:
        return self._prefix_parent

    @prefix_parent.setter
    def prefix_parent(self, prefix_parent: str):
        self._prefix_parent = prefix_parent
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
                        input_args, argument.type_converter.num_req_args
                    )
                    argument.process(args_use)
                    return args_remain

        return input_args

    def _num_params(self) -> int:
        return len(self.posargs) + len(self.varposargs) + len(self.kwargs)

    @property
    def args_values(self) -> Tuple[Any, ...]:
        res = [x.value for x in self.posargs]
        for arg in self.varposargs:
            res.extend(arg.value)

        return tuple(res)

    @property
    def args_values_with_excs(self) -> Tuple[Any, ...]:
        res = []
        for x in self.posargs:
            try:
                res.append(x.value)
            except Exception as e:
                res.append(e)
        for arg in self.varposargs:
            try:
                res.extend(arg.value)
            except Exception as e:
                res.append(e)

        return tuple(res)

    @property
    def kwargs_values(self) -> Dict[str, Any]:
        return {key: arg.value for key, arg in self.kwargs.items()}

    @property
    def kwargs_values_with_excs(self) -> Dict[str, Any]:
        res = {}
        for key, arg in self.kwargs.items():
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
            raise ParameterError(f"Error in ParameterGroup '{self.name}'") from e

    @property
    def cli_args(self) -> List[Argument]:
        posargs_args = [x for x in self.posargs if isinstance(x, Argument)]
        varposarg_args = [x for x in self.varposargs if isinstance(x, Argument)]
        kwargs_args = [x for x in self.kwargs.values() if isinstance(x, Argument)]
        return posargs_args + varposarg_args + kwargs_args

    @property
    def cli_opts(self) -> List[Union[Option, "ParameterGroup"]]:
        posargs_opts = [
            x for x in self.posargs if isinstance(x, (Option, ParameterGroup))
        ]
        varposarg_opts = [
            x for x in self.varposargs if isinstance(x, (Option, ParameterGroup))
        ]
        kwargs_opts = [
            x for x in self.kwargs.values() if isinstance(x, (Option, ParameterGroup))
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


def match_obj_filter_pg(
    obj_to_match: Any, cb: Callable[["ParameterGroup"], "ParameterGroup"]
) -> Callable[["ParameterGroup"], "ParameterGroup"]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(pg: "ParameterGroup") -> "ParameterGroup":
        if standardize_obj(pg.obj) == std_obj_to_match:
            return cb(pg)
        else:
            return pg

    return filtered_callback

EventCallbacks.default_event_obj_filters[Event.PG_POST_CREATE] = match_obj_filter_pg
