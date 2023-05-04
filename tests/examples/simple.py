"""
Very simple example of a CLI
"""
from pathlib import Path
from typing import List

from thermite import Config, run
from thermite.plugins.default_defs import defaults_cli_callback


def simple_example(param1: str, param2: float, param3: List[int], param4: Path):
    print(f"param1: {param1}")
    print(f"param2: {param2}")
    print(f"param3: {param3}")
    print(f"param4: {param4}")


if __name__ == "__main__":
    config = Config(cli_callbacks=[defaults_cli_callback])
    run(simple_example, config=config)
