import contextlib
import inspect
import io
import sys
import types
from inspect import Signature, classify_class_attrs
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    get_origin,
)

from attrs import mutable
from rich.console import Console

from thermite.exceptions import RichExcHandler, thermite_exc_handler
from thermite.help import CbHelp, CommandHelp, extract_descriptions
from thermite.utils import clify_argname

from .parameters import (
    ParameterGroup,
    process_class_to_param_group,
    process_function_to_param_group,
    process_instance_to_param_group,
)
from .preprocessing import split_and_expand, undeque
from .type_converters import CLIArgConverterStore


class UnknownCommandError(Exception):
    ...


@mutable
class Callback:
    callback: Callable[["Command"], None]
    triggers: List[str]
    descr: str

    def execute(self, cmd: "Command", args: Sequence[str]) -> Optional[Sequence[str]]:
        if args[0] in self.triggers:
            self.callback(cmd)
        if len(args) > 1:
            return args[1:]
        else:
            return None

    def help(self) -> CbHelp:
        return CbHelp(triggers=", ".join(self.triggers), descr=self.descr)


@mutable
class Subcommand:
    descr: Optional[str]
    attr_name: str


def extract_subcommands(
    return_type: Any, omit_dunder: bool = True
) -> Dict[str, Subcommand]:
    # First we check if it is a type or a function
    # there are not possilbe, only class instances
    if isinstance(return_type, types.FunctionType):
        raise Exception("Function type not allowed as return object for CLI")
    if get_origin(return_type) == Type:
        raise Exception("Class type is not allowed as return object for CLI")
    if return_type == Signature.empty:
        return {}
    if inspect.isclass(return_type):
        class_attrs = classify_class_attrs(return_type)
        res = {}
        for attr_name, _, _, obj in class_attrs:
            if omit_dunder and attr_name.startswith("__"):
                continue
            descr = extract_descriptions(obj)
            res[clify_argname(attr_name)] = Subcommand(
                descr=descr.short_descr, attr_name=attr_name
            )

        return res
    else:
        return {}


@mutable
class Command:
    param_group: ParameterGroup
    subcommands: Dict[str, Subcommand]
    prev_cmd: Optional["Command"] = None

    global_callbacks: ClassVar[List[Callback]] = []
    store: ClassVar[CLIArgConverterStore] = CLIArgConverterStore(add_defaults=True)

    def __attrs_post_init__(self):
        if len(self.param_group.cli_args) > 0 and len(self.subcommands) > 0:
            raise Exception("Can't have CLI that has subcommands and arguments")

    @classmethod
    def _from_function(cls, func: Callable, name: str):

        param_group = process_function_to_param_group(
            func, store=cls.store, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            subcommands=extract_subcommands(param_group._expected_ret_type),
        )

    @classmethod
    def _from_instance(cls, obj: Any, name: str):
        param_group = process_instance_to_param_group(
            obj, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            subcommands=extract_subcommands(obj.__class__),
        )

    @classmethod
    def _from_class(cls, klass: Type, name: str):
        param_group = process_class_to_param_group(
            klass, store=cls.store, name=name, child_prefix_omit_name=True
        )
        return cls(
            param_group=param_group,
            subcommands=extract_subcommands(param_group._expected_ret_type),
        )

    @classmethod
    def _global_callbacks_map(cls) -> Dict[str, Callback]:
        res = {}
        for cb in cls.global_callbacks:
            for trigger in cb.triggers:
                res[trigger] = cb

        return res

    @classmethod
    def from_obj(cls, obj: Any, name: str):
        if inspect.isfunction(obj):
            return cls._from_function(func=obj, name=name)
        elif inspect.isclass(obj):
            return cls._from_class(obj, name=name)
        else:
            raise NotImplementedError()

    def process(self, args: Sequence[str]) -> List[str]:
        input_args_deque = split_and_expand(args)

        global_cb_map = self._global_callbacks_map()

        while len(input_args_deque) > 0:
            input_args = input_args_deque.popleft()

            # first we check if we need to trigger one of the callbacks
            # only if that is not the case do we hand it to the
            # regular parameters; the callbacks are eager and need
            # to be processed first
            if len(input_args) > 0 and input_args[0] in global_cb_map:
                cb = global_cb_map[input_args[0]]
                args_return = cb.execute(self, input_args)
                if args_return is not None:
                    input_args_deque.appendleft(list(args_return))
            else:
                args_return = self.param_group.process(input_args)
                if len(args_return) > 0:
                    input_args_deque.appendleft(list(args_return))
                    if len(args_return) == len(input_args):
                        # we are finished
                        return undeque(input_args_deque)
        return []

    def invoke_subcommand(self, name: str) -> "Command":
        if name in self.subcommands:
            res_obj = self.param_group.value

            # we restrict subcommands to only work with instance objects
            # for now
            if isinstance(res_obj, types.FunctionType):
                raise Exception("Functions not supported as basis for subcommands")

            subcmd = self.subcommands[name]
            if subcmd.attr_name != "":
                subcommand = self.from_obj(
                    getattr(res_obj, subcmd.attr_name), name=name
                )
            else:
                subcommand = self.from_obj(getattr(res_obj, "__call__"), name=name)
            subcommand.prev_cmd = self

            return subcommand
        else:
            raise UnknownCommandError(f"Unknown subcommand {name}")

    @property
    def usage(self) -> str:
        usage_str = sys.argv[0]

        if len(self.param_group.cli_opts) > 0:
            usage_str += " [OPTIONS]"

        if len(self.subcommands) > 0:
            usage_str += " SUBCOMMAND"

        if len(self.param_group.cli_args) > 0:
            usage_str += " ARGS"

        return usage_str

    def help(self) -> CommandHelp:
        # argument help to show
        args = [x.help() for x in self.param_group.cli_args]
        cbs = [x.help() for x in self.global_callbacks]

        # the options don't need a special name or description;
        # that is intended for subgroups
        opt_group = self.param_group.help_opts_only()
        opt_group.name = "Options"
        opt_group.descr = None

        # last we need the subcommands and their descriptions
        subcommands = {key: obj.descr for key, obj in self.subcommands.items()}

        return CommandHelp(
            descr=self.param_group.descr,
            usage=self.usage,
            args=args,
            callbacks=cbs,
            opt_group=opt_group,
            subcommands=subcommands,
        )


def help_callback_func(cmd: Command) -> None:
    console = Console()
    console.print(cmd.help())
    sys.exit(0)


help_callback = Callback(
    callback=help_callback_func, triggers=["--help"], descr="Display the help message"
)


def noop_callback_func(cmd: Command) -> None:
    del cmd


noop_callback = Callback(
    callback=noop_callback_func,
    triggers=["--0"],
    descr="Works as a delimiter; no other operation",
)


def process_all_args(input_args: List[str], cmd: Command) -> Any:
    """
    Processes all input arguments in the context of a command.

    The arguments are processes for the current command, and then
    followed up with further processing in subcommands as needed.
    """
    ...
    # Note how to do eager callbacks?
    # how to do lazy callbacks?
    while len(input_args) > 0:
        input_args = cmd.process(input_args)
        if len(input_args) > 0:
            cmd = cmd.invoke_subcommand(input_args[0])
            input_args = input_args[1:]
        else:
            return cmd.param_group.value


def run(
    obj: Any,
    store: Optional[CLIArgConverterStore] = None,
    callbacks: Optional[List[Callback]] = None,
    add_help_cb: bool = True,
    exception_handlers: Optional[
        List[Callable[[Exception], Optional[Exception]]]
    ] = None,
    name: str = sys.argv[0],
    input_args: List[str] = sys.argv[1:],
    add_thermite_exc_handler: bool = True,
    add_rich_exc_handler: bool = True,
) -> Any:
    if store is not None:
        Command.store = store

    if callbacks is None:
        callbacks = []
    if add_help_cb:
        callbacks.append(help_callback)
    Command.global_callbacks = callbacks

    if exception_handlers is None:
        exception_handlers = []
    if add_thermite_exc_handler:
        exception_handlers.insert(0, thermite_exc_handler)
    if add_rich_exc_handler:
        exception_handlers.append(RichExcHandler())

    try:
        cmd = Command.from_obj(obj, name=name)
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
    name: Optional[str] = None,
    store: Optional[CLIArgConverterStore] = None,
    callbacks: Optional[List[Callback]] = None,
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
                store=store,
                callbacks=callbacks,
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
