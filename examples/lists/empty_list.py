"""
Very simple example of a CLI with empty list
"""
from typing import List

from thermite import (
    Config,
    ConstantTriggerProcessor,
    Event,
    Option,
    ParameterGroup,
    run,
)


def simple(x: List[int], y: List[int]):
    print(f"x: {x}")
    print(f"y: {y}")


def pg_empty_list(pg: ParameterGroup):
    assert isinstance(pg.params["x"], Option)
    pg.params["x"].processors.append(
        ConstantTriggerProcessor(triggers=["--x-empty"], res_type=[], constant=[])
    )
    return pg


if __name__ == "__main__":
    config = Config()
    config.event_cb_deco(Event.PG_POST_CREATE, simple)(pg_empty_list)
    run(simple, config=config)
