import inspect
from collections import defaultdict
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union

from attrs import field, mutable

from .type_converters import CLIArgConverterStore

if TYPE_CHECKING:
    from .command import CliCallback, Command
    from .parameters import ParameterGroup
    from .signatures import ObjSignature


class Event(Enum):
    START_ARGS_PRE_PROCESS = "START_ARGS_PRE_PROCESS"
    SIG_EXTRACT = "SIG_EXTRACT"
    CMD_POST_CREATE = "CMD_POST_CREATE"
    CMD_POST_PROCESS = "CMD_POST_PROCESS"
    PG_POST_CREATE = "PG_POST_CREATE"

    def __str__(self) -> str:
        return self.value


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
    obj_to_match: Any, cb: Callable[["Command"], "Command"]
) -> Callable[["Command"], "Command"]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(cmd: "Command") -> "Command":
        if standardize_obj(cmd.param_group.obj) == std_obj_to_match:
            return cb(cmd)
        else:
            return cmd

    return filtered_callback


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


def match_obj_filter_sig(
    obj_to_match: Any, cb: Callable[[Any, "ObjSignature"], "ObjSignature"]
) -> Callable[[Any, "ObjSignature"], "ObjSignature"]:
    std_obj_to_match = standardize_obj(obj_to_match)

    def filtered_callback(obj: Any, sig: "ObjSignature") -> "ObjSignature":
        if standardize_obj(obj) == std_obj_to_match:
            return cb(obj, sig)
        else:
            return sig

    return filtered_callback


@mutable
class EventCallbacks:
    add_defaults: bool = True

    def __attrs_post_init__(self):
        if self.add_defaults:
            self.add_default_events()

    def add_default_events(self):
        self.event_obj_filters[Event.SIG_EXTRACT] = match_obj_filter_sig
        self.event_obj_filters[Event.CMD_POST_CREATE] = match_obj_filter_cmd
        self.event_obj_filters[Event.CMD_POST_PROCESS] = match_obj_filter_cmd
        self.event_obj_filters[Event.PG_POST_CREATE] = match_obj_filter_pg

    event_cb_dict: Dict[Union[str, Event], List[Callable]] = field(
        factory=lambda: defaultdict(list)
    )
    event_obj_filters: Dict[
        Union[str, Event], Callable[[Any, Callable], Callable]
    ] = field(factory=lambda: defaultdict(None))

    def add_event_cb(self, event: Union[str, Event], cb: Callable, obj: Any = None):
        if obj is None:
            self.event_cb_dict[event].append(cb)
        else:
            if self.event_obj_filters[event] is None:
                raise Exception(f"No object filter for event {str(event)} registered")
            self.event_cb_dict[event].append(self.event_obj_filters[event](obj, cb))


@mutable(kw_only=True)
class Config:
    cli_callbacks: List["CliCallback"] = field(factory=list)
    cli_args_store: CLIArgConverterStore = field(
        factory=partial(CLIArgConverterStore, add_defaults=True)
    )
    event_callbacks: EventCallbacks = field(
        factory=partial(EventCallbacks, add_defaults=True)
    )

    def add_cli_callback(self, cb: "CliCallback"):
        self.cli_callbacks.append(cb)

    def get_event_cbs(self, event: Union[str, Event]) -> List[Callable]:
        return self.event_callbacks.event_cb_dict[event]
