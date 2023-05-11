"""
Very simple example of a CLI
"""
from thermite import Config, run
from thermite.plugins.default_defs import defaults_cli_callback


def simple(param1: str, param2: float):
    print(f"param1: {param1}")
    print(f"param2: {param2}")


if __name__ == "__main__":
    config = Config(cli_callbacks=[defaults_cli_callback])
    run(simple, config=config)
