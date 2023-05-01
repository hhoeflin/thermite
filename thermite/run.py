import contextlib
import io
import sys
from typing import Any, Callable, List, Optional, Union

from attrs import mutable

from thermite.exceptions import RichExcHandler, ThermiteExcHandler

from .callbacks import CliCallback, help_callback
from .command import Command
from .config import Config
from .exceptions import CommandError, ParameterError
from .type_converters import CLIArgConverterStore


def process_all_args(input_args: List[str], cmd: Command) -> Any:
    """
    Processes all input arguments in the context of a command.

    The arguments are processes for the current command, and then
    followed up with further processing in subcommands as needed.
    """
    while True:
        if len(input_args) > 0:
            input_args = cmd.process(input_args)
        if len(input_args) > 0:
            subcmd = cmd.get_subcommand(input_args[0])
            input_args = input_args[1:]
            cmd = subcmd
        else:
            try:
                return cmd.param_group.value
            except ParameterError as e:
                raise CommandError(
                    f"Error processing command {cmd.param_group.name}"
                ) from e


def run(
    obj: Any,
    config: Optional[Config] = None,
    add_help_cb: bool = True,
    exception_handlers: Optional[
        List[Callable[[Exception], Optional[Exception]]]
    ] = None,
    name: str = sys.argv[0],
    input_args: List[str] = sys.argv[1:],
    add_thermite_exc_handler: bool = True,
    add_rich_exc_handler: bool = True,
) -> Any:
    if config is None:
        config = Config()

    if add_help_cb:
        config.add_cli_callback(help_callback)

    if exception_handlers is None:
        exception_handlers = []
    if add_thermite_exc_handler:
        exception_handlers.append(ThermiteExcHandler(show_tb=False))
    if add_rich_exc_handler:
        exception_handlers.append(RichExcHandler())

    try:
        cmd = Command.from_obj(obj, name=name, config=config)
        return process_all_args(input_args=input_args, cmd=cmd)
    except Exception as input_e:
        # run through all exception handlers in order
        e: Optional[Exception] = input_e
        for handler in exception_handlers:
            if e is None:
                break
            try:
                e = handler(e)
            except Exception as raised_e:
                e = raised_e
            if not isinstance(e, Exception):
                break
        if e is not None:
            raise e from input_e


@mutable
class RunOutput:
    stdout: str
    stderr: str
    exit_code: Optional[Union[int, str]]
    exc: Optional[Exception]


def testing_runner(
    obj: Any,
    input_args: List[str],
    config: Optional[Config] = None,
    name: Optional[str] = None,
    exception_handlers: Optional[
        List[Callable[[Exception], Optional[Exception]]]
    ] = None,
    add_thermite_exc_handler: bool = True,
    add_rich_exc_handler: bool = True,
) -> RunOutput:
    if name is None:
        name = obj.__name__
    output = RunOutput(stdout="", stderr="", exit_code=0, exc=None)
    try:
        with contextlib.redirect_stdout(
            io.StringIO()
        ) as rout, contextlib.redirect_stderr(io.StringIO()) as rerr:
            run(
                obj=obj,
                config=config,
                exception_handlers=exception_handlers,
                input_args=input_args,
                add_thermite_exc_handler=add_thermite_exc_handler,
                add_rich_exc_handler=add_rich_exc_handler,
            )
    except Exception as e:
        output.exc = e
        output.exit_code = 1
    except SystemExit as e:
        output.exit_code = e.code

    output.stdout = rout.getvalue()
    output.stderr = rerr.getvalue()
    return output
