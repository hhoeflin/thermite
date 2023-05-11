"""
Very simple example of a CLI with a list
"""
from typing import List

from thermite import Config, run


def simple(x: List[int]):
    print(f"x: {x}")


if __name__ == "__main__":
    config = Config()
    run(simple, config=config)
