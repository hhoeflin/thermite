"""
CLI with subcommands.
"""
from pathlib import Path
from typing import List

from thermite import run
from thermite.config import Config
from thermite.plugins.default_defs import defaults_cli_callback


class Subcommands:
    def __init__(self, global_param1: Path):
        pass

    def cmd1(self, param1: str):
        """First subcommand"""
        pass


if __name__ == "__main__":
    config = Config(cli_callbacks=[defaults_cli_callback])
    run(Subcommands, config=config)
