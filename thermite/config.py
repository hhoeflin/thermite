import inspect
from collections import defaultdict
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Type, Union

from attrs import field, mutable

from .cli_args_splitter import EagerCliArgsSplitter
from .type_converters import CLIArgConverterStore

if TYPE_CHECKING:
    from .command import CliCallback


class Event(Enum):
    START_ARGS_PRE_PROCESS = "START_ARGS_PRE_PROCESS"
    SIG_EXTRACT = "SIG_EXTRACT"
    CMD_POST_CREATE = "CMD_POST_CREATE"
    CMD_POST_PROCESS = "CMD_POST_PROCESS"
    PG_POST_CREATE = "PG_POST_CREATE"
    CMD_FINISH = "CMD_FINISH"

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


@mutable
class EventCallbacks:
    add_defaults: bool = True

    event_cb_dict: Dict[Union[str, Event], List[Callable]] = field(
        factory=lambda: defaultdict(list)
    )
    event_obj_filters: Dict[
        Union[str, Event], Callable[[Callable, Any], Callable]
    ] = field(factory=lambda: defaultdict(None))
    default_event_obj_filters: ClassVar[
        Dict[Union[str, Event], Callable[[Any, Callable], Callable]]
    ] = defaultdict(None)

    def __attrs_post_init__(self):
        if self.add_defaults:
            self.add_default_events()

    def add_default_events(self):
        self.event_obj_filters.update(self.default_event_obj_filters.items())

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
    cli_callbacks_top_level: List["CliCallback"] = field(factory=list)
    cli_args_store: CLIArgConverterStore = field(
        factory=partial(CLIArgConverterStore, add_defaults=True)
    )
    event_callbacks: EventCallbacks = field(
        factory=partial(EventCallbacks, add_defaults=True)
    )
    SplitterClass: Type = EagerCliArgsSplitter

    def add_cli_callback(self, cb: "CliCallback"):
        self.cli_callbacks.append(cb)

    def get_event_cbs(self, event: Union[str, Event]) -> List[Callable]:
        return self.event_callbacks.event_cb_dict[event]

    def event_cb_deco(self, event: Union[str, Event], obj: Any = None):
        def add_event_cb_inner(cb: Callable):
            self.event_callbacks.add_event_cb(event=event, cb=cb, obj=obj)
            return cb

        return add_event_cb_inner
