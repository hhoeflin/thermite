from typing import Dict, List, Optional, Union

from attrs import mutable
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


def opt_help_list_to_table(opts: List[OptHelp]) -> Optional[Table]:
    if len(opts) == 0:
        return None
    else:
        opt_grid = Table(expand=True, show_header=False, box=box.SIMPLE, leading=1)
        opt_grid.add_column("Trigger")
        opt_grid.add_column("Type")
        opt_grid.add_column("Default")
        opt_grid.add_column("Description")

        for opt in opts:
            opt_grid.add_row(opt.triggers, opt.type_descr, opt.default, opt.descr)

        return opt_grid


def arg_help_list_to_table(args: List[ArgHelp]) -> Optional[Table]:
    if len(args) == 0:
        return None
    else:
        opt_grid = Table(expand=True, show_header=False, box=box.SIMPLE, leading=1)
        opt_grid.add_column("Name")
        opt_grid.add_column("Type")
        opt_grid.add_column("Default")
        opt_grid.add_column("Description")

        for arg in args:
            opt_grid.add_row(arg.name, arg.type_descr, arg.default, arg.descr)

        return opt_grid


@mutable(slots=False, kw_only=True)
class OptionGroupHelp:
    name: Optional[str]
    descr: Optional[str]
    gen_opts: List[OptHelp]
    opt_groups: List["OptionGroupHelp"]

    def __rich__(self) -> Panel:
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

        group = Group(*elements)
        outpanel = Panel(group, title=self.name, expand=True, title_align="left")

        return outpanel


def create_commands_panel(subcommands: Dict[str, str]) -> Optional[Panel]:
    if len(subcommands) == 0:
        return None
    else:
        cmd_grid = Table.grid()
        cmd_grid.add_column("Name")
        cmd_grid.add_column("Description")  # trigger

        for cmd, descr in subcommands.items():
            cmd_grid.add_row(cmd, descr)

        return Panel(cmd_grid, title="Commands")


@mutable(slots=False, kw_only=True)
class CommandHelp:
    descr: Optional[str]
    usage: str
    subcommands: Dict[str, str]
    args: List[ArgHelp]
    opt_group: OptionGroupHelp

    def __rich__(self) -> Group:

        elements: List[Union[ConsoleRenderable, RichCast, str, Panel]] = []

        if self.descr is not None:
            elements.append(Text(self.descr))

        elements.append(Text(self.usage))
        cmd_panel = create_commands_panel(self.subcommands)
        if cmd_panel is not None:
            elements.append(cmd_panel)

        arg_table = arg_help_list_to_table(self.args)
        if arg_table is not None:
            elements.append(arg_table)

        elements.append(rich_cast(self.opt_group))
        return Group(*elements)
