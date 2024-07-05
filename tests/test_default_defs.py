from copy import deepcopy
from pathlib import Path
from typing import List

from attrs import field, mutable

from thermite.command import Command
from thermite.config import Config, EventCallback
from thermite.parameters.group import ParameterGroup
from thermite.plugins.default_defs import defaults_cli_callback
from thermite.run import runner_testing

from .examples.simple import simple_example
from .examples.subcommands import Subcommands


@mutable
class DebugPgRecord(EventCallback):
    """Class to record the status of cmd during testing."""

    copy_post_create: List[ParameterGroup] = field(factory=list)
    copy_post_process: List[ParameterGroup] = field(factory=list)

    def cmd_post_create(self, cmd: Command) -> Command:
        self.copy_post_create.append(deepcopy(cmd.param_group))
        return cmd

    def cmd_post_process(self, cmd: Command) -> Command:
        self.copy_post_process.append(deepcopy(cmd.param_group))
        return cmd


def test_simple_ex_default_defs():
    config = Config(cli_callbacks=[defaults_cli_callback])
    pg_recorder = DebugPgRecord()
    config.event_callbacks.append(pg_recorder)
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
    assert len(pg_recorder.copy_post_create) > 0
    pg_before = pg_recorder.copy_post_create[0]
    assert len(pg_recorder.copy_post_process) > 0
    pg_after = pg_recorder.copy_post_process[0]

    # values before were unset
    assert pg_before["param1"].default_value == ...
    assert pg_before["param2"].default_value == ...
    assert pg_before["param3"].default_value == ...
    assert pg_before["param4"].default_value == ...
    # values after were changed
    assert pg_after is not None
    assert pg_after["param1"].default_value == "foo"
    assert pg_after["param2"].default_value == 3
    assert pg_after["param3"].default_value == [1, 2]
    assert pg_after["param4"].default_value == Path("foobar/file")


def test_subcmds_ex_default_defs():
    config = Config(cli_callbacks=[defaults_cli_callback])
    pg_recorder = DebugPgRecord()
    config.event_callbacks.append(pg_recorder)
    output = runner_testing(
        Subcommands,
        config=config,
        input_args=[
            "--defaults-file",
            str(
                Path(__file__).parent / "examples" / "subcommands_defaults.yml#version1"
            ),
            "--global-param1",
            "file.yml",
            "--global-param2",
            "test",
            "example1",
        ],
    )
    print(output.stdout)

    # now check that at the beginning, the defaults where not there
    # and afterwards they were changed
    assert len(pg_recorder.copy_post_create) > 1
    pg_before = pg_recorder.copy_post_create[1]
    assert len(pg_recorder.copy_post_process) > 1
    pg_after = pg_recorder.copy_post_process[1]
    # values before were unset
    assert pg_before["param1"].default_value == ...
    # values after were changed
    assert pg_after["param1"].default_value == "foo"
