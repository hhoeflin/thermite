from functools import partial

from attrs import mutable

from thermite import BasicCLIArgConverter, Config, run


@mutable
class Fraction:
    numerator: int
    denominator: int


def fraction_convert(x: str):
    return Fraction(int(x.split("/")[0]), int(x.split("/")[1]))


config = Config()
config.cli_args_store.add_converter_factory(
    partial(
        BasicCLIArgConverter.factory,
        supported_type=Fraction,
        conv_func=fraction_convert,
    ),
    11,
)


def fraction(x: Fraction):
    print(f"{x.numerator}/{x.denominator} = {x.numerator/x.denominator}")


if __name__ == "__main__":
    run(fraction, config=config)
