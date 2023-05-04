"""
CLI with subcommands.
"""
from pathlib import Path
from typing import List

from thermite import run
from thermite.callbacks import noop_callback, show_bindings_callback
from thermite.config import Config
from thermite.plugins.default_defs import defaults_cli_callback


class Subcommands:
    def __init__(self, global_param1: Path, global_param2: List[str]):
        pass

    def example1(self, param1: str):
        """First example"""
        pass

    def example2(self, param: int):
        """Second example"""
        pass


if __name__ == "__main__":
    config = Config(
        cli_callbacks=[defaults_cli_callback, noop_callback, show_bindings_callback]
    )
    run(Subcommands, config=config)
