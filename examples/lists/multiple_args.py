"""
Very simple example of a CLI with multiple lists as arguments
"""
from typing import Any, List

from thermite import CliParamKind, Config, Event, ObjSignature, run
from thermite.callbacks import noop_callback


def simple(x: List[int], y: List[int]):
    print(f"x: {x}")
    print(f"y: {y}")


def opt_to_arg(sig: ObjSignature, _: Any):
    sig.params["x"].cli_kind = CliParamKind.ARGUMENT
    sig.params["y"].cli_kind = CliParamKind.ARGUMENT

    return sig


if __name__ == "__main__":
    config = Config()
    config.event_cb_deco(Event.SIG_EXTRACT, simple)(opt_to_arg)
    config.add_cli_callback(noop_callback)
    run(simple, config=config)
