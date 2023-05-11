"""
Very simple example of a CLI with a list
and variable number of values for the option
"""
from typing import List

from thermite import Config, Event, Option, ParameterGroup, run


def simple(x: List[int]):
    print(f"x: {x}")


def pg_multi_opt(pg: ParameterGroup) -> ParameterGroup:
    pg["x"].processors[0] = pg["x"].processors[0].to_convert_trigger_processor()
    return pg


if __name__ == "__main__":
    config = Config()
    config.event_cb_deco(Event.PG_POST_CREATE, simple)(pg_multi_opt)
    run(simple, config=config)
