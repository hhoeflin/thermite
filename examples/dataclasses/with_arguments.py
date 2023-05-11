from typing import Any

from attrs import mutable

from thermite import CliParamKind, Config, Event, ObjSignature, run

config = Config()


@mutable
class Fraction:
    numerator: int
    denominator: int


def fraction(x: Fraction):
    print(f"{x.numerator}/{x.denominator} = {x.numerator/x.denominator}")


@config.event_cb_deco(Event.SIG_EXTRACT, Fraction)
def to_args(sig: ObjSignature, _: Any):
    sig.params["numerator"].cli_kind = CliParamKind.ARGUMENT
    sig.params["denominator"].cli_kind = CliParamKind.ARGUMENT
    return sig


if __name__ == "__main__":
    run(fraction, config=config)
