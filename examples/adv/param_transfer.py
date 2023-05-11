"""
Example of parameter transfer
"""
from pathlib import Path
from typing import Any

from thermite import Config, Event, ObjSignature, process_function_to_obj_signature, run


def process_file(input_file: Path, param1: str, param2: float):
    ...


def process_dir(input_dir: Path, **kwargs):
    print(f"input_dir: {input_dir}")
    print(f"kwargs: {kwargs}")
    # for input_file in input_dir.glob("*"):
    #    process_file(input_file, **kwargs)


def transfer_params(sig: ObjSignature, _: Any):
    proc_file_sig = process_function_to_obj_signature(process_file)

    del sig.params["kwargs"]
    del proc_file_sig.params["input_file"]
    sig.params.update(proc_file_sig.params)

    return sig


if __name__ == "__main__":
    config = Config()
    config.event_cb_deco(Event.SIG_EXTRACT, process_dir)(transfer_params)
    run(process_dir, config=config)
