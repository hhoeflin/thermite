import inspect
from collections.abc import MutableMapping
from functools import partial
from typing import Any, Callable, List

from attrs import Factory, field, mutable
from beartype.door import is_bearable

from .command import Callback, Command
from .type_converters import CLIArgConverterStore


class CmdPostProcStore(MutableMapping):
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

    def __getitem__(self, key) -> Callable[["Command"], "Command"]:
        return self.data[self._standardize(key)]

    def __setitem__(self, key, value: Callable[["Command"], "Command"]):
        if not is_bearable(value, Callable[[Command], Command]):
            raise ValueError(
                "value has to be a function taking and returning a Command obj"
            )
        self.data[self._standardize(key)] = value

    def __delitem__(self, key):
        del self.data[self._standardize(key)]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)


@mutable
class Config:
    callbacks: List[Callback] = field(factory=list)
    cli_args_store: CLIArgConverterStore = field(
        factory=partial(CLIArgConverterStore, add_defaults=True)
    )
    cmd_post_proc_store: CmdPostProcStore = field(factory=CmdPostProcStore)
