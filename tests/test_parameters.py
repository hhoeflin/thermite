from pathlib import Path
from typing import List, Tuple

import pytest
from attrs import mutable

from thermite.exceptions import (
    TooFewInputsError,
    UnexpectedTriggerError,
    UnspecifiedOptionError,
)
from thermite.parameters import BoolOption, KnownLenArg, KnownLenOpt, Option, Parameter
from thermite.type_converters import ListCLIArgConverter, PathCLIArgConverter


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
            name="a",
            descr="test",
            pos_triggers=pos_triggers,
            neg_triggers=neg_triggers,
            prefix=prefix,
            default_value=...,
        )
        if val_exp == ...:
            # raises an error
            with pytest.raises(UnexpectedTriggerError):
                opt.process_split(args)
        else:
            ret_args = opt.process_split(args)
            assert opt.value == val_exp
            assert ret_args == ret_args_exp

    def test_unused(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("-a",),
            neg_triggers=(),
            default_value=...,
        )
        with pytest.raises(UnspecifiedOptionError):
            opt.value

    def test_too_few_args(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("-a",),
            neg_triggers=(),
            default_value=...,
        )
        with pytest.raises(TooFewInputsError):
            opt.process_split([])

    def test_multiple_process(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            default_value=...,
            multiple=True,
        )
        opt.process_split(["--yes"])
        assert opt.value is True

        opt.process_split(["--no"])
        assert opt.value is False

    def test_isinstance_option(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            default_value=...,
        )
        assert isinstance(opt, Option)

    def test_isinstance_parameter(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            default_value=...,
        )
        assert isinstance(opt, Parameter)


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
            name="a",
            descr="Path option",
            triggers=triggers,
            default_value=...,
            type_converter=PathCLIArgConverter(Path),
            target_type_str="Path",
            multiple=False,
            prefix=prefix,
        )
        if val_exp == ...:
            # raises an error
            with pytest.raises(UnexpectedTriggerError):
                opt.process_split(args)
        else:
            ret_args = opt.process_split(args)
            assert opt.value == val_exp
            assert ret_args == ret_args_exp

    def test_too_few_args(self):
        opt = KnownLenOpt(
            name="a",
            descr="Path option",
            triggers=("--path", "-p"),
            default_value=[],
            type_converter=PathCLIArgConverter(Path),
            target_type_str="Path",
            multiple=True,
        )
        with pytest.raises(TooFewInputsError):
            opt.process_split(["--path"])

    def test_path_opt_multi(self, store):
        opt = KnownLenOpt(
            name="a",
            descr="Path option",
            triggers=("--path", "-p"),
            default_value=[],
            type_converter=ListCLIArgConverter(List[Path], store=store),
            target_type_str="Path",
            multiple=True,
        )
        opt.process_split(["--path", "/a/b"])
        opt.process_split(["--path", "/c"])
        assert opt.value == [Path("/a/b"), Path("/c")]


class TestKnownLenArgs:
    def path_arg(self) -> KnownLenArg:
        arg = KnownLenArg(
            name="a",
            descr="Path option",
            default_value=...,
            type_converter=PathCLIArgConverter(Path),
            target_type_str="Path",
            callback=None,
        )
        return arg

    def test_path_arg(self):
        path_arg = self.path_arg()
        path_arg.process_split(["/a/b"])
        assert path_arg.value == Path("/a/b")
