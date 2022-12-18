from pathlib import Path
from typing import Tuple

import pytest
from attrs import mutable

from thermite.exceptions import TooFewArgsError, UnexpectedTriggerError
from thermite.parameters import (
    BoolOption,
    KnownLenArgs,
    KnownLenOpt,
    NoOpOption,
    Option,
    Parameter,
)


@mutable
class FakeOption:
    triggers: Tuple[str, ...]


def test_protocol_checks_option_correct():
    fake = FakeOption(("a",))
    assert not isinstance(fake, Option)


class TestBoolOption:
    @pytest.mark.parametrize(
        "pos_triggers,neg_triggers,prefix,args,val_exp,ret_args_exp",
        [
            (("-y", "--yes"), ("-n", "--no"), "", ["-y"], True, []),
            (("-y", "--yes"), ("-n", "--no"), "", ["--yes"], True, []),
            (("-y", "--yes"), ("-n", "--no"), "", ["-n"], False, []),
            (("-y", "--yes"), ("-n", "--no"), "", ["--no"], False, []),
            (("-y", "--yes"), ("-n", "--no"), "", ["-y", "other"], True, ["other"]),
            (("-y", "--yes"), ("-n", "--no"), "", ["-a"], ..., []),
            (("-y", "--yes"), ("-n", "--no"), "group", ["-y"], ..., []),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-yes"], True, []),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--yes"], ..., []),
            (("-y", "--yes"), ("-n", "--no"), "group", ["-n"], ..., []),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-no"], False, []),
        ],
    )
    def test_normal(
        self, pos_triggers, neg_triggers, prefix, args, val_exp, ret_args_exp
    ):
        """Test that BoolOption works as expected."""

        opt = BoolOption(
            descr="test",
            pos_triggers=pos_triggers,
            neg_triggers=neg_triggers,
            prefix=prefix,
        )
        if val_exp == ...:
            # raises an error
            with pytest.raises(UnexpectedTriggerError):
                opt.process(args)
        else:
            ret_args = opt.process(args)
            assert opt.value == val_exp
            assert ret_args == ret_args_exp

    def test_unused(self):
        opt = BoolOption(descr="test", pos_triggers=("-a",), neg_triggers=())
        assert opt.value is ...

    def test_too_few_args(self):
        opt = BoolOption(descr="test", pos_triggers=("-a",), neg_triggers=())
        with pytest.raises(TooFewArgsError):
            opt.process([])

    def test_multiple_process(self):
        opt = BoolOption(descr="test", pos_triggers=("--yes",), neg_triggers=("--no",))
        opt.process(["--yes"])
        assert opt.value is True

        opt.process(["--no"])
        assert opt.value is False

    def test_isinstance_option(self):
        opt = BoolOption(descr="test", pos_triggers=("--yes",), neg_triggers=("--no",))
        assert isinstance(opt, Option)

    def test_isinstance_parameter(self):
        opt = BoolOption(descr="test", pos_triggers=("--yes",), neg_triggers=("--no",))
        assert isinstance(opt, Parameter)


class TestNoOpOption:
    def test_usage(self):
        opt = NoOpOption(descr="test", triggers=("-0",))
        proc_ret = opt.process(["-0", "other"])
        assert proc_ret == ["other"]
        assert opt.value is None


class TestKnownLenOpt:
    @pytest.mark.parametrize(
        "triggers,prefix,args,val_exp,ret_args_exp",
        [
            (("--path", "-p"), "", ["--path", "/a/b"], Path("/a/b"), []),
            (("--path", "-p"), "", ["-p", "/a/b"], Path("/a/b"), []),
            (
                ("--path", "-p"),
                "",
                ["--path", "/a/b", "other"],
                Path("/a/b"),
                ["other"],
            ),
            (("--path", "-p"), "", ["-a", "/a/b"], ..., []),
            (("--path", "-p"), "", ["--foo", "/a/b"], ..., []),
            (("--path", "-p"), "group", ["--group-path", "/a/b"], Path("/a/b"), []),
            (("--path", "-p"), "group", ["--path", "/a/b"], ..., []),
            (("--path", "-p"), "group", ["-p", "/a/b"], ..., []),
            (
                ("--path", "-p"),
                "group",
                ["--group-path", "/a/b", "other"],
                Path("/a/b"),
                ["other"],
            ),
            (("--path", "-p"), "group", ["-a", "/a/b"], ..., []),
            (("--path", "-p"), "group", ["--foo", "/a/b"], ..., []),
        ],
    )
    def test_normal(self, triggers, prefix, args, val_exp, ret_args_exp):
        """Test that BoolOption works as expected."""

        opt = KnownLenOpt(
            descr="Path option",
            triggers=triggers,
            value=...,
            nargs=1,
            type_converter=Path,
            callback=None,
            multiple=False,
            prefix=prefix,
        )
        if val_exp == ...:
            # raises an error
            with pytest.raises(UnexpectedTriggerError):
                opt.process(args)
        else:
            ret_args = opt.process(args)
            assert opt.value == val_exp
            assert ret_args == ret_args_exp

    def test_too_few_args(self):
        opt = KnownLenOpt(
            descr="Path option",
            triggers=("--path", "-p"),
            value=...,
            nargs=1,
            type_converter=Path,
            callback=None,
            multiple=True,
        )
        with pytest.raises(TooFewArgsError):
            opt.process(["--path"])

    def test_path_opt_multi(self):
        opt = KnownLenOpt(
            descr="Path option",
            triggers=("--path", "-p"),
            value=...,
            nargs=1,
            type_converter=Path,
            callback=None,
            multiple=True,
        )
        opt.process(["--path", "/a/b"])
        opt.process(["--path", "/c"])
        assert opt.value == [Path("/a/b"), Path("/c")]


class TestKnownLenArgs:
    def path_arg(self) -> KnownLenArgs:
        arg = KnownLenArgs(
            descr="Path option",
            value=...,
            nargs=1,
            type_converter=Path,
            callback=None,
        )
        return arg

    def test_path_arg(self):
        path_arg = self.path_arg()
        path_arg.process(["/a/b"])
        assert path_arg.value == Path("/a/b")
