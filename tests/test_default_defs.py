from copy import deepcopy
from pathlib import Path
from typing import List

from attrs import field, mutable

from thermite.command import Command
from thermite.config import Config, Event
from thermite.plugins.default_defs import defaults_cli_callback
from thermite.run import runner_testing

from .examples.simple import simple_example


@mutable
class DebugCmdRecord:
    """Class to record the status of cmd during testing."""

    cmd_copies: List[Command] = field(factory=list)

    def __call__(self, cmd: Command) -> Command:
        self.cmd_copies.append(deepcopy(cmd))
        return cmd


def test_simple_ex_default_defs():
    config = Config(cli_callbacks=[defaults_cli_callback])
    cmd_post_create_recorder = DebugCmdRecord()
    cmd_post_process_recorder = DebugCmdRecord()
    config.event_callbacks.add_event_cb(
        event=Event.CMD_POST_CREATE, cb=cmd_post_create_recorder
    )
    config.event_callbacks.add_event_cb(
        event=Event.CMD_POST_PROCESS, cb=cmd_post_process_recorder
    )
    output = runner_testing(
        simple_example,
        config=config,
        input_args=[
            "--defaults-file",
            str(Path(__file__).parent / "examples" / "simple_defaults.yml"),
        ],
    )
    print(output.stdout)

    # now check that at the beginning, the defaults where not there
    # and afterwards they were changed
    cmd_before = cmd_post_create_recorder.cmd_copies[0]
    cmd_after = cmd_post_process_recorder.cmd_copies[0]
    # values before were unset
    cmd_before.param_group["param1"].default_value == ...
    cmd_before.param_group["param2"].default_value == ...
    cmd_before.param_group["param3"].default_value == ...
    cmd_before.param_group["param4"].default_value == ...
    # values after were changed
    cmd_after.param_group["param1"].default_value == "foo"
    cmd_after.param_group["param2"].default_value == 3
    cmd_after.param_group["param3"].default_value == [1, 2]
    cmd_after.param_group["param4"].default_value == Path("foobar/file")
