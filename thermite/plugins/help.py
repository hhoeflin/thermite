import inspect
import re
import sys
from typing import Any, Dict, List, Optional, Union, _type_repr, get_args

from attrs import field, mutable
from rich import box
from rich.console import Console, ConsoleRenderable, Group, RichCast
from rich.panel import Panel
from rich.protocol import rich_cast
from rich.table import Table
from rich.text import Text

from thermite.command import CliCallback, Command
from thermite.config import Config
from thermite.parameters import (
    Argument,
    MultiConvertTriggerProcessor,
    Option,
    ParameterGroup,
    TriggerProcessor,
)


def clean_type_str(obj) -> str:
    type_descr = _type_repr(obj)

    # clean out all modulenames
    p = re.compile(r"([a-zA-Z0-9_]+\.)([a-zA-Z0-9_]+)")
    num_repl = 1
    while num_repl > 0:
        type_descr, num_repl = p.subn(r"\2", type_descr)

    return type_descr


@mutable()
class ProcessorHelp:
    triggers: str
    type_descr: str


def processor_to_processor_help(x: TriggerProcessor) -> ProcessorHelp:
    if isinstance(x, MultiConvertTriggerProcessor):
        return ProcessorHelp(
            triggers=", ".join(x.triggers),
            type_descr=clean_type_str(get_args(x.res_type)[0]) + "*",
        )
    else:
        return ProcessorHelp(
            triggers=", ".join(x.triggers), type_descr=clean_type_str(x.res_type)
        )


@mutable()
class OptHelp:
    processors: List[ProcessorHelp]
    default: str
    descr: str


def option_to_help(opt: Option) -> OptHelp:
    default_str = str(opt.default_value) if opt.default_value != ... else ""

    return OptHelp(
        processors=[processor_to_processor_help(x) for x in opt.processors],
        default=default_str,
        descr=opt.descr if opt.descr is not None else "",
    )


@mutable()
class ArgHelp:
    name: str
    type_descr: str
    default: str
    descr: str


def argument_to_help(arg: Argument) -> ArgHelp:
    default_str = str(arg.default_value) if arg.default_value != ... else ""
    return ArgHelp(
        name=arg.name,
        type_descr=clean_type_str(arg.res_type),
        default=default_str,
        descr=arg.descr if arg.descr is not None else "",
    )


@mutable()
class CbHelp:
    triggers: str
    descr: str


def clicb_to_help(clicb: CliCallback) -> CbHelp:
    return CbHelp(triggers=", ".join(clicb.triggers), descr=clicb.descr)


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
        return len(self.gen_opts) == 0 and len(self.opt_groups) == 0


def param_group_to_help_opts_only(
    pg: ParameterGroup, config: Config
) -> OptionGroupHelp:
    cli_opts_single = [x for x in pg.cli_opts.values() if isinstance(x, Option)]
    cli_opts_group = [x for x in pg.cli_pgs.values() if isinstance(x, ParameterGroup)]

    opt_groups_help = [
        param_group_to_help_opts_only(x, config=config) for x in cli_opts_group
    ]
    opt_grp_help = OptionGroupHelp(
        name=pg.name,
        descr=pg.short_descr,
        gen_opts=[option_to_help(x) for x in cli_opts_single],
        opt_groups=[x for x in opt_groups_help if not x.empty],
    )
    for cb in config.get_event_cbs("HELP_PG_CREATE"):
        opt_grp_help = cb(pg, opt_grp_help)

    return opt_grp_help


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
    short_descr: Optional[str]
    long_descr: Optional[str]
    usage: str
    subcommands: Dict[str, Optional[str]]
    args: List[ArgHelp]
    callbacks: List[CbHelp]
    opt_group: OptionGroupHelp

    def __rich__(self) -> Group:
        elements: List[Union[ConsoleRenderable, RichCast, str, Panel]] = []

        if self.short_descr is not None:
            elements.append(Text(self.short_descr + "\n"))

        elements.append(Text("Usage: " + self.usage + "\n"))

        if self.long_descr is not None:
            elements.append(Text(inspect.cleandoc(self.long_descr) + "\n"))

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


def command_to_help(cmd: Command) -> CommandHelp:
    # argument help to show
    args = [argument_to_help(x) for x in cmd.param_group.cli_args_recursive.values()]
    cbs = [clicb_to_help(x) for x in cmd.config.cli_callbacks + cmd.local_cli_callbacks]

    # the options don't need a special name or description;
    # that is intended for subgroups
    opt_group = param_group_to_help_opts_only(cmd.param_group, config=cmd.config)
    opt_group.name = "Options"
    opt_group.descr = None

    # last we need the subcommands and their descriptions
    subcommands = {key: obj.descr for key, obj in cmd.subcommands.items()}

    cmd_help = CommandHelp(
        short_descr=cmd.param_group.short_descr,
        long_descr=cmd.param_group.long_descr,
        usage=cmd.usage,
        args=args,
        callbacks=cbs,
        opt_group=opt_group,
        subcommands=subcommands,
    )
    for cb in cmd.config.get_event_cbs("HELP_CMD_CREATE"):
        cmd_help = cb(cmd, cmd_help)
    return cmd_help


def help_callback_func(cmd: Command) -> None:
    console = Console()
    console.print(command_to_help(cmd))
    sys.exit(0)


help_callback = CliCallback(
    callback=help_callback_func, triggers=["--help"], descr="Display the help message"
)
