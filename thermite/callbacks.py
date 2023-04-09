import sys

from prettyprinter import install_extras, pprint
from rich.console import Console

from .command import Callback, Command


def help_callback_func(cmd: Command) -> None:
    console = Console()
    console.print(cmd.help())
    sys.exit(0)


help_callback = Callback(
    callback=help_callback_func, triggers=["--help"], descr="Display the help message"
)


def noop_callback_func(cmd: Command) -> None:
    del cmd


noop_callback = Callback(
    callback=noop_callback_func,
    triggers=["--0"],
    descr="Works as a delimiter; no other operation",
)


def show_bindings_func(cmd: Command) -> None:
    install_extras(include=["attrs"])
    pprint(cmd)


show_bindings_callback = Callback(
    callback=show_bindings_func,
    triggers=["--show-bindings"],
    descr="Show the state of the cmds.",
)
