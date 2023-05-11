"""
Very simple example of a CLI
"""
from typing import Any

from thermite import CliParamKind, Config, Event, ObjSignature, run

config = Config()


def simple(param1: str, param2: float):
    print(f"param1: {param1}")
    print(f"param2: {param2}")


@config.event_cb_deco(Event.SIG_EXTRACT, simple)
def add_help_cb(sig: ObjSignature, _: Any):
    sig.short_descr = "A simple example"
    sig.long_descr = """A long description for the command.
                        Maybe over several lines.
                     """

    sig.params["param1"].descr = "Description for parameter 1."
    sig.params["param2"].descr = "Description for parameter 2."

    sig.params["param1"].cli_kind = CliParamKind.ARGUMENT

    return sig


if __name__ == "__main__":
    run(simple, config=config)
