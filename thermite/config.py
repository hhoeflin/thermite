import inspect
from functools import partial
from typing import TYPE_CHECKING, Any, List, Tuple, Type

from attrs import field, mutable

from .cli_args_splitter import EagerCliArgsSplitter
from .type_converters import CLIArgConverterStore

if TYPE_CHECKING:
    from .command import CliCallback, Command
    from .parameters import ParameterGroup
    from .signatures import ObjSignature


@mutable
class EventCallback:
    def cmd_post_create(self, cmd: "Command") -> "Command":
        return cmd

    def start_args_pre_process(
        self, cmd: "Command", input_args: List[str]
    ) -> Tuple["Command", List[str]]:
        return (cmd, input_args)

    def sig_extract(self, sig: "ObjSignature", obj: Any) -> "ObjSignature":
        del obj
        return sig

    def cmd_post_process(self, cmd: "Command") -> "Command":
        return cmd

    def pg_post_create(self, pg: "ParameterGroup") -> "ParameterGroup":
        return pg

    def cmd_finish(self, cmd: "Command") -> "Command":
        return cmd


def standardize_obj(obj: Any) -> Any:
    if inspect.isfunction(obj):
        return obj
    elif inspect.ismethod(obj):
        return obj.__func__
    elif isinstance(obj, type):
        return obj
    else:
        return obj.__class__


@mutable(kw_only=True)
class Config:
    cli_callbacks: List["CliCallback"] = field(factory=list)
    cli_callbacks_top_level: List["CliCallback"] = field(factory=list)
    cli_args_store: CLIArgConverterStore = field(
        factory=partial(CLIArgConverterStore, add_defaults=True)
    )
    event_callbacks: List[EventCallback] = field(factory=list)
    SplitterClass: Type = EagerCliArgsSplitter
