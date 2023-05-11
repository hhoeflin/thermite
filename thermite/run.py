import contextlib
import io
import sys
from typing import Any, Callable, List, Optional, Union

from attrs import mutable

from thermite.exceptions import RichExcHandler, ThermiteExcHandler
from thermite.plugins.help import help_callback

from .command import CliCallback, Command
from .config import Config, Event
from .exceptions import CommandError, ParameterError


def process_all_args(input_args: List[str], cmd: Command) -> Any:
    """
    Processes all input arguments in the context of a command.

    The arguments are processes for the current command, and then
    followed up with further processing in subcommands as needed.
    """
    while True:
        if len(input_args) > 0:
            input_args = cmd.process(input_args)
        # CMD_POST_PROCESS Event start
        for cb in cmd.config.get_event_cbs(Event.CMD_POST_PROCESS):
            cmd = cb(cmd)
        # CMD_POST_PROCESS Event end
        if len(input_args) > 0:
            subcmd = cmd.get_subcommand(input_args[0])
            input_args = input_args[1:]
            # CMD_POST_CREATE Event start
            for cb in cmd.config.get_event_cbs(Event.CMD_POST_CREATE):
                subcmd = cb(subcmd)
            # CMD_POST_CREATE Event end
            cmd = subcmd
        else:
            # CMD_FINISH Event start
            for cb in cmd.config.get_event_cbs(Event.CMD_FINISH):
                cmd = cb(cmd)
            # CMD_FINISH Event end
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
    cli_callbacks_top_level: Optional[List["CliCallback"]] = None,
) -> Any:
    if config is None:
        config = Config()
    if cli_callbacks_top_level is None:
        cli_callbacks_top_level = []

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
        cmd.local_cli_callbacks = cli_callbacks_top_level
        # CMD_POST_CREATE Event start
        for cb in config.get_event_cbs(Event.CMD_POST_CREATE):
            cmd = cb(cmd)
        # CMD_POST_CREATE Event end
        # START_ARGS_PRE_PROCESS Event start
        for cb in config.get_event_cbs(Event.START_ARGS_PRE_PROCESS):
            cmd, input_args = cb(cmd, input_args)
        # START_ARGS_PRE_PROCESS Event end
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


def runner_testing(
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
