import inspect
from abc import abstractmethod
from collections.abc import MutableMapping
from functools import partial
from typing import Any, Callable, Generic, List, TypeVar

from attrs import Factory, field, mutable
from beartype.door import is_bearable

from .command import CliCallback, Command
from .parameters import ParameterGroup
from .type_converters import CLIArgConverterStore


class CmdPostProc:
    @abstractmethod
    def post_process(self, cmd: Command):
        pass

    @abstractmethod
    def subcommand(self, cmd: Command):
        pass


VT = TypeVar("VT")


@mutable
class Signature:
    ...


def standardize_obj(obj: Any) -> Any:
    if inspect.isfunction(obj):
        return obj
    elif inspect.ismethod(obj):
        return obj.__func__
    elif isinstance(obj, type):
        return obj
    else:
        return obj.__class__


def match_obj_filter_cmd(
    obj_to_match: Any, cb: Callable[[Command], Command]
) -> Callable[[Command], Command]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(cmd: Command) -> Command:
        if standardize_obj(cmd.param_group.obj) == std_obj_to_match:
            return cb(cmd)
        else:
            return cmd

    return filtered_callback


def match_obj_filter_pg(
    obj_to_match: Any, cb: Callable[[ParameterGroup], ParameterGroup]
) -> Callable[[ParameterGroup], ParameterGroup]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(pg: ParameterGroup) -> ParameterGroup:
        if standardize_obj(pg.obj) == std_obj_to_match:
            return cb(pg)
        else:
            return pg

    return filtered_callback


def match_obj_filter_sig(
    obj_to_match: Any, cb: Callable[[Any, Signature], Signature]
) -> Callable[[Any, Signature], Signature]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(obj: Any, sig: Signature) -> Signature:
        if standardize_obj(obj) == std_obj_to_match:
            return cb(obj, sig)
        else:
            return sig

    return filtered_callback


class ThermiteStore(MutableMapping, Generic[VT]):
    def __init__(self, dict_update=None):
        self.data = {}
        if dict_update is not None:
            for k, v in dict_update.items():
                self[k] = v

    @staticmethod
    def _standardize(obj: Any) -> Any:
        return standardize_obj(obj)

    def __getitem__(self, key) -> VT:
        return self.data[self._standardize(key)]

    def __setitem__(self, key, value: VT):
        self.data[self._standardize(key)] = value

    def __delitem__(self, key):
        del self.data[self._standardize(key)]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)


@mutable
class ConfigStores:
    cli_args: CLIArgConverterStore = field(
        factory=partial(CLIArgConverterStore, add_defaults=True)
    )
    # sig_extract: ThermiteStore[Callable[[Signature], Signature]] = field(
    #    factory=ThermiteStore
    # )
    # cmd_post_create: ThermiteStore[Callable[[Command], Command]] = field(
    #    factory=ThermiteStore
    # )
    # cmd_post_process: ThermiteStore[CmdPostProc] = field(factory=ThermiteStore)
    # pg_post_create: ThermiteStore[Callable[[ParameterGroup], ParameterGroup]] = field(
    #    factory=ThermiteStore
    # )


@mutable
class ConfigCallbacks:
    sig_extract: List[Callable[[Signature], Signature]] = field(factory=list)
    cmd_post_create: List[Callable[[Command], Command]] = field(factory=list)
    cmd_post_process: List[Callable[[Command], Command]] = field(factory=list)
    pg_post_create: List[Callable[[ParameterGroup], ParameterGroup]] = field(
        factory=list
    )
    cli: List[CliCallback] = field(factory=list)


@mutable
class Config:
    stores: ConfigStores = field(factory=ConfigStores)
    callbacks: ConfigCallbacks = field(factory=ConfigCallbacks)

    def add_cli_callback(self, cb: CliCallback):
        self.callbacks.cli.append(cb)
