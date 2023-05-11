from attrs import mutable

from thermite import run


@mutable
class Fraction:
    numerator: int
    denominator: int


def fraction(x: Fraction):
    print(f"{x.numerator}/{x.denominator} = {x.numerator/x.denominator}")


if __name__ == "__main__":
    run(fraction)
