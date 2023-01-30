from pathlib import Path
from typing import List, Tuple

import pytest
from attrs import mutable

from thermite.exceptions import UnexpectedTriggerError, UnspecifiedOptionError
from thermite.parameters import (
    BoolOption,
    KnownLenArg,
    KnownLenOpt,
    Option,
    OptionError,
    Parameter,
)
from thermite.type_converters import ListCLIArgConverter, PathCLIArgConverter


@mutable
class FakeOption:
    triggers: Tuple[str, ...]


def test_protocol_checks_option_correct():
    fake = FakeOption(("a",))
    assert not isinstance(fake, Option)


class TestBoolOption:
    @pytest.mark.parametrize(
        "pos_triggers,neg_triggers,prefix,args,val_exp",
        [
            (("-y", "--yes"), ("-n", "--no"), "", ["-y"], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["--yes"], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["-n"], False),
            (("-y", "--yes"), ("-n", "--no"), "", ["--no"], False),
            (("-y", "--yes"), ("-n", "--no"), "", ["-y", "other"], OptionError),
            (("-y", "--yes"), ("-n", "--no"), "", ["-a"], UnexpectedTriggerError),
            (("-y", "--yes"), ("-n", "--no"), "group", ["-y"], UnexpectedTriggerError),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-yes"], True),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-n"],
                UnexpectedTriggerError,
            ),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["--yes"],
                UnexpectedTriggerError,
            ),
            (("-y", "--yes"), ("-n", "--no"), "group", ["-n"], UnexpectedTriggerError),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-no"], False),
        ],
    )
    def test_normal(self, pos_triggers, neg_triggers, prefix, args, val_exp):
        """Test that BoolOption works as expected."""

        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=pos_triggers,
            neg_triggers=neg_triggers,
            prefix=prefix,
            default_value=...,
        )
        if type(val_exp) == type and issubclass(val_exp, Exception):
            # raises an error
            with pytest.raises(val_exp):
                opt.bind(args)
        else:
            opt.bind(args)
            assert opt.value == val_exp

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
        with pytest.raises(OptionError):
            opt.bind([])

    def test_multiple_bind(self):
        opt = BoolOption(
            name="a",
            descr="test",
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            default_value=...,
            multiple=True,
        )
        opt.bind(["--yes"])
        assert opt.value is True

        opt.bind(["--no"])
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
        "triggers,prefix,args,val_exp",
        [
            (("--path", "-p"), "", ["--path", "/a/b"], Path("/a/b")),
            (("--path", "-p"), "", ["-p", "/a/b"], Path("/a/b")),
            (("--path", "-p"), "", ["--path", "/a/b", "other"], OptionError),
            (("--path", "-p"), "", ["-a", "/a/b"], UnexpectedTriggerError),
            (("--path", "-p"), "", ["--foo", "/a/b"], UnexpectedTriggerError),
            (("--path", "-p"), "group", ["--group-path", "/a/b"], Path("/a/b")),
            (("--path", "-p"), "group", ["--path", "/a/b"], UnexpectedTriggerError),
            (("--path", "-p"), "group", ["-p", "/a/b"], UnexpectedTriggerError),
            (
                ("--path", "-p"),
                "group",
                ["--group-path", "/a/b", "other"],
                OptionError,
            ),
            (("--path", "-p"), "group", ["-a", "/a/b"], UnexpectedTriggerError),
            (("--path", "-p"), "group", ["--foo", "/a/b"], UnexpectedTriggerError),
        ],
    )
    def test_normal(self, triggers, prefix, args, val_exp):
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
        if type(val_exp) == type and issubclass(val_exp, Exception):
            # raises an error
            with pytest.raises(val_exp):
                opt.bind(args)
        else:
            opt.bind(args)
            assert opt.value == val_exp

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
        with pytest.raises(OptionError):
            opt.bind(["--path"])

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
        opt.bind(["--path", "/a/b"])
        opt.bind(["--path", "/c"])
        assert opt.value == [Path("/a/b"), Path("/c")]


class TestKnownLenArgs:
    def path_arg(self) -> KnownLenArg:
        arg = KnownLenArg(
            name="a",
            descr="Path option",
            default_value=...,
            type_converter=PathCLIArgConverter(Path),
            target_type_str="Path",
        )
        return arg

    def test_path_arg(self):
        path_arg = self.path_arg()
        path_arg.bind(["/a/b"])
        assert path_arg.value == Path("/a/b")
