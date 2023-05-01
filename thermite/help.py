from typing import Any, Dict, List, Optional, Union

from attrs import field, mutable
from rich import box
from rich.console import ConsoleRenderable, Group, RichCast
from rich.panel import Panel
from rich.protocol import rich_cast
from rich.table import Table
from rich.text import Text


@mutable(kw_only=True)
class ProcessorHelp:
    triggers: str
    type_descr: str


@mutable(kw_only=True)
class OptHelp:
    processors: List[ProcessorHelp]
    default: str
    descr: str


@mutable(kw_only=True)
class ArgHelp:
    name: str
    type_descr: str
    default: str
    descr: str


@mutable(kw_only=True)
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
            for i, processor in enumerate(opt.processors):
                opt_grid.add_row(
                    Text(processor.triggers),
                    Text(processor.type_descr),
                    Text(opt.default) if i == 0 else "",
                    Text(opt.descr) if i == 0 else "",
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


@mutable(kw_only=True)
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

        # cast groups to rich, but add a newline before
        for grp in self.opt_groups:
            if len(elements) > 0:
                elements.append(Text())
            elements.append(rich_cast(grp))

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


@mutable(kw_only=True)
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
