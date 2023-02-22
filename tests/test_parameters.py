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
    ParameterGroup,
    process_class_to_param_group,
)
from thermite.type_converters import CLIArgConverterStore, PathCLIArgConverter

from .examples.app import NestedClass


@mutable
class FakeOption:
    triggers: Tuple[str, ...]


def test_protocol_checks_option_correct():
    fake = FakeOption(("a",))
    assert not isinstance(fake, Option)


class TestBoolOption:
    @pytest.mark.parametrize(
        "pos_triggers,neg_triggers,prefix,args,return_args,val_exp",
        [
            (("-y", "--yes"), ("-n", "--no"), "", ["-y"], None, True),
            (("-y", "--yes"), ("-n", "--no"), "", ["--yes"], None, True),
            (("-y", "--yes"), ("-n", "--no"), "", ["-n"], None, False),
            (("-y", "--yes"), ("-n", "--no"), "", ["--no"], None, False),
            (("-y", "--yes"), ("-n", "--no"), "", ["-y", "other"], ["other"], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["-a"], None, UnexpectedTriggerError),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-y"],
                None,
                UnexpectedTriggerError,
            ),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-yes"], None, True),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-n"],
                None,
                UnexpectedTriggerError,
            ),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["--yes"],
                None,
                UnexpectedTriggerError,
            ),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-n"],
                None,
                UnexpectedTriggerError,
            ),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-no"], None, False),
        ],
    )
    def test_normal(
        self, pos_triggers, neg_triggers, prefix, args, return_args, val_exp
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
        if type(val_exp) == type and issubclass(val_exp, Exception):
            # raises an error
            with pytest.raises(val_exp):
                opt.bind(args)
        else:
            bind_return = opt.bind(args)
            assert opt.value == val_exp
            assert bind_return == return_args

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
        "triggers,prefix,args,return_args, val_exp",
        [
            (("--path", "-p"), "", ["--path", "/a/b"], None, Path("/a/b")),
            (("--path", "-p"), "", ["-p", "/a/b"], None, Path("/a/b")),
            (
                ("--path", "-p"),
                "",
                ["--path", "/a/b", "other"],
                ["other"],
                Path("/a/b"),
            ),
            (("--path", "-p"), "", ["-a", "/a/b"], None, UnexpectedTriggerError),
            (("--path", "-p"), "", ["--foo", "/a/b"], None, UnexpectedTriggerError),
            (("--path", "-p"), "group", ["--group-path", "/a/b"], None, Path("/a/b")),
            (
                ("--path", "-p"),
                "group",
                ["--path", "/a/b"],
                None,
                UnexpectedTriggerError,
            ),
            (("--path", "-p"), "group", ["-p", "/a/b"], None, UnexpectedTriggerError),
            (
                ("--path", "-p"),
                "group",
                ["--group-path", "/a/b", "other"],
                ["other"],
                Path("/a/b"),
            ),
            (("--path", "-p"), "group", ["-a", "/a/b"], None, UnexpectedTriggerError),
            (
                ("--path", "-p"),
                "group",
                ["--foo", "/a/b"],
                None,
                UnexpectedTriggerError,
            ),
        ],
    )
    def test_normal(self, triggers, prefix, args, return_args, val_exp):
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
            bind_return = opt.bind(args)
            assert opt.value == val_exp
            assert bind_return == return_args

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
            type_converter=PathCLIArgConverter(Path),
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


class TestParamGroup:
    def param_group(self) -> ParameterGroup:
        res = process_class_to_param_group(
            NestedClass,
            store=CLIArgConverterStore(),
            name="test",
            child_prefix_omit_name=True,
        )
        res.default_value = NestedClass(a=1)
        return res

    def test_default(self):
        param_group = self.param_group()
        assert param_group.value == NestedClass(a=1)

    def test_single_incomplete_bind(self):
        param_group = self.param_group()
        param_group.bind(["--b", "test2"])
        with pytest.raises(UnspecifiedOptionError):
            param_group.value

    def test_single_complete_bind(self):
        param_group = self.param_group()
        param_group.bind(["--a", "2"])
        assert param_group.value == NestedClass(a=2)

    def test_both_bind(self):
        param_group = self.param_group()
        param_group.bind(["--a", "2"])
        param_group.bind(["--b", "test2"])
        assert param_group.value == NestedClass(a=2, b="test2")
