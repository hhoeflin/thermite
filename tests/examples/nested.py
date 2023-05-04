"""
Nested example of a CLI with single function
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from thermite import run


@dataclass
class Config:
    """
    Configuration parameters.

    Args:
        param1: First parameter
        param2: Second parameter
    """

    param1: str
    param2: Path = Path("foo/bar")


def example(param1: str, param2: float, param3: List[int], config: Config):
    print(f"param1: {param1}")
    print(f"param2: {param2}")
    print(f"param3: {param3}")
    print(f"config: {config}")


if __name__ == "__main__":
    run(example)
