import sys

from prettyprinter import install_extras, pprint

from .command import CliCallback, Command


def noop_callback_func(cmd: Command) -> None:
    del cmd


noop_callback = CliCallback(
    callback=noop_callback_func,
    triggers=["--0"],
    descr="Works as a delimiter; no other operation",
)


def show_bindings_func(cmd: Command) -> None:
    install_extras(include=["attrs"])
    pprint(cmd)


show_bindings_callback = CliCallback(
    callback=show_bindings_func,
    triggers=["--show-bindings"],
    descr="Show the state of the cmds.",
)
