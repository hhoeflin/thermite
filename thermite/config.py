import inspect
from collections.abc import MutableMapping, abstractmethod
from functools import partial
from typing import Any, Callable, Generic, List, TypeVar

from attrs import Factory, field, mutable
from beartype.door import is_bearable

from .command import Callback, Command
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


class ThermiteStore(MutableMapping, Generic[VT]):
    def __init__(self, dict_update=None):
        self.data = {}
        if dict_update is not None:
            for k, v in dict_update.items():
                self[k] = v

    @staticmethod
    def _standardize(obj: Any) -> Any:
        if inspect.isfunction(obj):
            return obj
        elif inspect.ismethod(obj):
            return obj.__func__
        elif isinstance(obj, type):
            return obj
        else:
            return obj.__class__

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
    sig_extract: ThermiteStore[Callable[[Signature], Signature]] = field(
        factory=ThermiteStore
    )
    cmd_post_create: ThermiteStore[Callable[[Command], Command]] = field(
        factory=ThermiteStore
    )
    cmd_post_process: ThermiteStore[CmdPostProc] = field(factory=ThermiteStore)
    pg_post_create: ThermiteStore[Callable[[ParameterGroup], ParameterGroup]] = field(
        factory=ThermiteStore
    )


@mutable
class Config:
    callbacks: List[Callback] = field(factory=list)
    stores: ConfigStores = field(factory=ConfigStores)
