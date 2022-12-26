import inspect
from abc import abstractmethod
from functools import partial
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from attrs import field, mutable
from beartype.door import is_bearable

from thermite.exceptions import (
    DuplicatedTriggerError,
    NothingProcessedError,
    TooFewInputsError,
    UnexpectedReturnTypeError,
    UnexpectedTriggerError,
    UnspecifiedArgumentError,
    UnspecifiedObjError,
    UnspecifiedOptionError,
)

from .base import Argument, Option, Parameter

EllipsisType = type(...)


@mutable(slots=False, kw_only=True)
class Group:
    descr: str = ""
    obj: Any = None
    expected_ret_type: object = None

    @property
    @abstractmethod
    def args(self) -> Tuple[Any, ...]:
        ...

    @property
    @abstractmethod
    def kwargs(self) -> Dict[str, Any]:
        ...

    def _exec_obj(self) -> Any:
        if self.obj is None:
            raise UnspecifiedObjError()
        if inspect.isfunction(self.obj):
            res_obj = self.obj(*self.args, **self.kwargs)
            if not is_bearable(res_obj, self.expected_ret_type):
                raise UnexpectedReturnTypeError(
                    f"Expected return type {str(self.expected_ret_type)} "
                    f"but got {str(type(res_obj))}"
                )
        elif inspect.isclass(self.obj):
            res_obj = self.obj(*self.args, **self.kwargs)
        else:
            raise NotImplementedError()

        return res_obj


@mutable(slots=False, kw_only=True)
class OptionGroup(Group):
    _opts: Dict[str, Union[Option, "OptionGroup"]] = field(factory=dict, init=False)
    _stored_trigger_mapping: Optional[Dict[str, Union[Option, "OptionGroup"]]] = field(
        default=None, init=False
    )
    _prefix: str = ""
    _name: str = ""
    _num_splits_processed: int = field(default=0, init=False)
    _default_value: Any = field(default=...)

    def _set_prefix_children(self):
        for option in self._options.values():
            option.prefix = self.child_prefix

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

    def _mapping_final_trigger_to_opt(self) -> Dict[str, Union[Option, "OptionGroup"]]:
        res: Dict[str, Union[Option, "OptionGroup"]] = {}
        for opt in self._opts.values():
            final_triggers = opt.final_triggers
            for trigger in final_triggers:
                if trigger in res:
                    raise DuplicatedTriggerError(
                        f"Trigger {trigger} in options {opt} and {res[trigger]}"
                    )
                else:
                    res[trigger] = opt
        return res

    @property
    def final_triggers(self) -> Set[str]:
        return set(self._mapping_final_trigger_to_opt().keys())

    @property
    def final_trigger_help(self) -> str:
        raise NotImplementedError()

    def process_split(self, args: Sequence[str]) -> List[str]:
        if self._stored_trigger_mapping is None:
            self._stored_trigger_mapping = self._mapping_final_trigger_to_opt()

        if len(args) == 0:
            raise TooFewInputsError("Processing options requires more than 0 args.")

        if not args[0].startswith("-"):
            raise Exception("First argument has to start with a '-': {args[0]}")

        if args[0] in self._stored_trigger_mapping:
            self._num_splits_processed += 1
            return self._stored_trigger_mapping[args[0]].process_split(args)
        else:
            raise UnexpectedTriggerError(f"Trigger {args[0]} not in mapping")

    def add_opt(self, name: str, option: Option):
        # ensure that the new option has the right prefix
        if name in self._opts:
            raise Exception(f"{name} already a stored option.")
        option.prefix = self.child_prefix
        self._opts[name] = option

    @property
    def args(self) -> Tuple[Any, ...]:
        return ()

    @property
    def kwargs(self) -> Dict[str, Any]:
        return {key: opt.value for key, opt in self._opts.items()}

    @property
    def value(self) -> Any:
        if self._num_splits_processed > 0:
            return self._exec_obj()
        elif self._default_value != ...:
            return self._default_value
        else:
            raise UnspecifiedOptionError(
                "No Options in the group specified and and has no default"
            )


@mutable(slots=False, kw_only=True)
class ArgumentGroup(Group):
    _args: Dict[str, Argument] = field(factory=dict, init=False)

    def add_arg(self, name: str, argument: Argument):
        # ensure that the new option has the right prefix
        if name in self._args:
            raise Exception(f"{name} already a stored argument.")
        self._args[name] = argument

    def process_split(self, args: Sequence[str]) -> List[str]:
        if len(args) == 0:
            raise TooFewInputsError("Processing options requires more than 0 args.")

        if args[0].startswith("-"):
            raise Exception("First argument can't be a trigger: {args[0]}")

        # go through the stored arguments to the first unprocessed one
        for argument in self._args.values():
            if argument.unset:
                return argument.process_split(args)

        raise NothingProcessedError(f"No arguments were processed for {args}")

    @property
    def args(self) -> Tuple[Any, ...]:
        for arg_name, arg in self._args.items():
            if arg.value == ...:
                raise UnspecifiedArgumentError(
                    f"Argument {arg_name} was not specified and has no default"
                )
        return tuple((arg.value for arg in self._args.values()))

    @property
    def kwargs(self) -> Dict[str, Any]:
        return {}


@mutable(slots=False, kw_only=True)
class ParameterGroup(Group):
    _arg_group: ArgumentGroup = field(factory=ArgumentGroup, init=False)
    _opt_group: OptionGroup = field(
        factory=partial(OptionGroup, descr="", prefix="", name=""), init=False
    )

    def add_param(self, name: str, param: Parameter):
        if isinstance(param, Argument):
            self._arg_group.add_arg(name, param)
        elif isinstance(param, Option):
            self._opt_group.add_opt(name, param)
        else:
            raise TypeError(f"Unknown type {type(param)}")

    def process_split(self, args: Sequence[str]) -> List[str]:
        if len(args) == 0:
            return []

        if args[0].startswith("-"):
            return self._opt_group.process_split(args)
        else:
            return self._arg_group.process_split(args)

    @property
    def args(self) -> Tuple[Any, ...]:
        return self._arg_group.args

    @property
    def kwargs(self) -> Dict[str, Any]:
        return self._opt_group.kwargs

    @property
    def value(self) -> Any:
        return self._exec_obj()
