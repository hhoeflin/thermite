"""
Nested example of a CLI with single function
"""
from pathlib import Path
from typing import List

from thermite import run


class Config:
    """
    Configuration parameters.

    Args:
        config_param1: First parameter
        config_para2: Second parameter
    """

    def __init__(self, config_param1: str, config_para2: Path):
        pass


def example(param1: str, param2: float, param3: List[int], param4: Config):
    print(f"param1: {param1}")
    print(f"param2: {param2}")
    print(f"param3: {param3}")
    print(f"param4: {param4}")


if __name__ == "__main__":
    run(example)
