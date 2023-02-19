import inspect
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from attrs import mutable
from docstring_parser import Docstring, parse
from rich import box
from rich.console import ConsoleRenderable, Group, RichCast
from rich.panel import Panel
from rich.protocol import rich_cast
from rich.table import Table
from rich.text import Text


@mutable(slots=False, kw_only=True)
class OptHelp:
    triggers: str
    type_descr: str
    default: str
    descr: str


@mutable(slots=False, kw_only=True)
class ArgHelp:
    name: str
    type_descr: str
    default: str
    descr: str


@mutable(slots=False, kw_only=True)
class CbHelp:
    triggers: str
    descr: str


def opt_help_list_to_table(opts: List[OptHelp]) -> Optional[Table]:
    if len(opts) == 0:
        return None
    else:
        opt_grid = Table(
            expand=False,
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            show_edge=False,
        )
        opt_grid.add_column("Trigger")
        opt_grid.add_column("Type")
        opt_grid.add_column("Default")
        opt_grid.add_column("Description")

        for opt in opts:
            opt_grid.add_row(
                Text(opt.triggers),
                Text(opt.type_descr),
                Text(opt.default),
                Text(opt.descr),
            )

        return opt_grid


def cb_help_list_to_table(cbs: List[CbHelp]) -> Optional[Panel]:
    if len(cbs) == 0:
        return None
    else:
        cb_grid = Table(
            expand=False,
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            show_edge=False,
        )
        cb_grid.add_column("Trigger")
        cb_grid.add_column("Description")

        for cb in cbs:
            cb_grid.add_row(
                Text(cb.triggers),
                Text(cb.descr),
            )

        outpanel = Panel(
            cb_grid, title="Eager Callbacks", expand=True, title_align="left"
        )
        return outpanel


def arg_help_list_to_table(args: List[ArgHelp]) -> Optional[Panel]:
    if len(args) == 0:
        return None
    else:
        arg_grid = Table(
            expand=False,
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            show_edge=False,
        )
        arg_grid.add_column("Name")
        arg_grid.add_column("Type")
        arg_grid.add_column("Default")
        arg_grid.add_column("Description")

        for arg in args:
            arg_grid.add_row(
                Text(arg.name), Text(arg.type_descr), Text(arg.default), Text(arg.descr)
            )

        outpanel = Panel(arg_grid, title="Arguments", expand=True, title_align="left")
        return outpanel


@mutable(slots=False, kw_only=True)
class OptionGroupHelp:
    name: Optional[str]
    descr: Optional[str]
    gen_opts: List[OptHelp]
    opt_groups: List["OptionGroupHelp"]

    def __rich__(self) -> Union[Panel, Text]:
        """
        Create a panel with a table for the options and subtable if
        there are opt_groups included.
        """
        elements: List[Union[ConsoleRenderable, RichCast, str]] = []
        if self.descr is not None:
            elements.append(Text(self.descr))

        opt_grid = opt_help_list_to_table(self.gen_opts)
        if opt_grid is not None:
            elements.append(opt_grid)

        elements.extend([rich_cast(x) for x in self.opt_groups])

        if len(elements) > 0:
            group = Group(*elements)
            outpanel = Panel(group, title=self.name, expand=True, title_align="left")

            return outpanel
        else:
            return Text()

    @property
    def empty(self) -> bool:
        return (
            len(self.gen_opts) == 0 and len(self.opt_groups) == 0 and self.descr is None
        )


def create_commands_panel(subcommands: Dict[str, Optional[str]]) -> Optional[Panel]:
    if len(subcommands) == 0:
        return None
    else:
        cmd_grid = Table(
            expand=False,
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            show_edge=False,
        )
        cmd_grid = Table.grid(padding=(0, 2))
        cmd_grid.add_column("Name")
        cmd_grid.add_column("Description")  # trigger

        for cmd, descr in subcommands.items():
            cmd_grid.add_row(Text(cmd), Text(descr) if descr is not None else None)

        return Panel(cmd_grid, title="Commands", expand=True, title_align="left")


@mutable(slots=False, kw_only=True)
class CommandHelp:
    descr: Optional[str]
    usage: str
    subcommands: Dict[str, Optional[str]]
    args: List[ArgHelp]
    callbacks: List[CbHelp]
    opt_group: OptionGroupHelp

    def __rich__(self) -> Group:

        elements: List[Union[ConsoleRenderable, RichCast, str, Panel]] = []

        if self.descr is not None:
            elements.append(Text(self.descr + "\n"))

        elements.append(Text(self.usage + "\n"))

        cb_table = cb_help_list_to_table(self.callbacks)
        if cb_table is not None:
            elements.append(cb_table)

        arg_table = arg_help_list_to_table(self.args)
        if arg_table is not None:
            elements.append(arg_table)

        if not self.opt_group.empty:
            elements.append(rich_cast(self.opt_group))

        cmd_panel = create_commands_panel(self.subcommands)
        if cmd_panel is not None:
            elements.append(cmd_panel)
        return Group(*elements)


@mutable()
class Descriptions:
    short_descr: Optional[str]
    long_descr: Optional[str]
    args_doc_dict: Dict[str, Optional[str]]


def doc_to_dict(doc_parsed: Docstring) -> Dict[str, Optional[str]]:
    res: Dict[str, Optional[str]] = defaultdict(lambda: None)
    res.update({x.arg_name: x.description for x in doc_parsed.params})
    return res


def extract_descriptions(obj: Any) -> Descriptions:
    if inspect.isclass(obj):
        klass_doc = inspect.getdoc(obj)
        if klass_doc is not None:
            klass_doc_parsed = parse(klass_doc)
            short_description = klass_doc_parsed.short_description
            long_description = klass_doc_parsed.long_description
        else:
            long_description = None
            short_description = None
        func = obj.__init__
    else:
        func = obj
        short_description = None
        long_description = None

    # preprocess the documentation
    func_doc = inspect.getdoc(func)
    if func_doc is not None:
        doc_parsed = parse(func_doc)
        long_description = (
            long_description
            if long_description is not None
            else doc_parsed.long_description
        )
        short_description = (
            short_description
            if short_description is not None
            else doc_parsed.short_description
        )
        args_doc_dict = doc_to_dict(doc_parsed)
    else:
        short_description = None
        args_doc_dict = defaultdict(lambda: None)
    return Descriptions(
        short_descr=short_description,
        long_descr=long_description,
        args_doc_dict=args_doc_dict,
    )
