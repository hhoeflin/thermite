import inspect
from typing import Any, Dict, List, Sequence, Set, Tuple, Union

from attrs import field, mutable
from beartype.door import is_bearable

from thermite.exceptions import (
    DuplicatedTriggerError,
    UnexpectedReturnTypeError,
    UnexpectedTriggerError,
    UnprocessedArgumentError,
    UnspecifiedObjError,
)

from .base import Argument, Option, Parameter

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class ParameterGroup:
    descr: str = ""
    obj: Any = None
    expected_ret_type: object = None
    posargs: List[Union[Parameter, "ParameterGroup"]] = field(factory=list)
    varposargs: List[Union[Parameter, "ParameterGroup"]] = field(factory=list)
    kwargs: Dict[str, Union[Parameter, "ParameterGroup"]] = field(factory=dict)
    _num_splits_processed: int = field(default=0, init=False)
    _prefix: str = ""
    _name: str = ""
    _default_value: Any = field(default=...)

    def _exec_obj(self) -> Any:
        if self.obj is None:
            raise UnspecifiedObjError()
        if inspect.isfunction(self.obj):
            res_obj = self.obj(*self.args_values, **self.kwargs_values)
            if not is_bearable(res_obj, self.expected_ret_type):
                raise UnexpectedReturnTypeError(
                    f"Expected return type {str(self.expected_ret_type)} "
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

    def process_split(self, input_args: Sequence[str]) -> List[str]:
        if len(input_args) == 0:
            return []

        if input_args[0].startswith("-"):
            all_opts = self.cli_opts
            opts_by_trigger = map_trigger_to_opts(all_opts)
            if input_args[0] in opts_by_trigger:
                self._num_splits_processed += 1
                return opts_by_trigger[input_args[0]].process_split(input_args)
            else:
                raise UnexpectedTriggerError(f"No option with trigger {input_args[0]}")

        else:
            for argument in self.cli_args:
                if argument.unset:
                    return argument.process_split(input_args)

            raise UnprocessedArgumentError(
                f"No unset argument for {' '.join(input_args)}"
            )

    @property
    def args_values(self) -> Tuple[Any, ...]:
        res = [x.value for x in self.posargs]
        for arg in self.varposargs:
            res.extend(arg.value)

        return tuple(res)

    @property
    def kwargs_values(self) -> Dict[str, Any]:
        return {key: arg.value for key, arg in self.kwargs.items()}

    @property
    def value(self) -> Any:
        return self._exec_obj()

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
    def final_triggers(self) -> Set[str]:
        all_triggers: Set[str] = set()
        for opt in self.cli_opts:
            all_triggers.update(opt.final_triggers)
        return all_triggers


def map_trigger_to_opts(
    opts: List[Union[Option, ParameterGroup]]
) -> Dict[str, Union[Option, ParameterGroup]]:
    res: Dict[str, Union[Option, ParameterGroup]] = {}
    for opt in opts:
        final_triggers = opt.final_triggers
        for trigger in final_triggers:
            if trigger in res:
                raise DuplicatedTriggerError(
                    f"Trigger {trigger} in options {opt} and {res[trigger]}"
                )
            else:
                res[trigger] = opt
    return res
