import sys

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
