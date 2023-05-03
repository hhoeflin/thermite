import inspect
from pathlib import Path
from typing import List, Tuple

import pytest
from attrs import asdict, mutable

from thermite.config import Config
from thermite.exceptions import ParameterError, TriggerError, UnspecifiedOptionError
from thermite.parameters import (
    Argument,
    ConvertListTriggerProcessor,
    ConvertOnceTriggerProcessor,
    ConvertReplaceTriggerProcessor,
    Option,
    OptionError,
    Parameter,
    ParameterGroup,
    bool_option,
    process_class_to_param_group,
)
from thermite.signatures import CliParamKind, ParameterSignature
from thermite.type_converters import (
    CLIArgConverterStore,
    PathCLIArgConverter,
    TooFewArgsError,
)

from .examples import NestedClass


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
            (("-y", "--yes"), ("-n", "--no"), "", ["-y"], [], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["--yes"], [], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["-n"], [], False),
            (("-y", "--yes"), ("-n", "--no"), "", ["--no"], [], False),
            (("-y", "--yes"), ("-n", "--no"), "", ["-y", "other"], ["other"], True),
            (("-y", "--yes"), ("-n", "--no"), "", ["-a"], [], TriggerError),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-y"],
                [],
                TriggerError,
            ),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-yes"], [], True),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-n"],
                [],
                TriggerError,
            ),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["--yes"],
                [],
                TriggerError,
            ),
            (
                ("-y", "--yes"),
                ("-n", "--no"),
                "group",
                ["-n"],
                [],
                TriggerError,
            ),
            (("-y", "--yes"), ("-n", "--no"), "group", ["--group-no"], [], False),
        ],
    )
    def test_normal(
        self, pos_triggers, neg_triggers, prefix, args, return_args, val_exp
    ):
        """Test that BoolOption works as expected."""

        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=pos_triggers,
            neg_triggers=neg_triggers,
            prefix=prefix,
        )
        if type(val_exp) == type and issubclass(val_exp, Exception):
            # raises an error
            with pytest.raises(val_exp):
                opt.process(args)
        else:
            process_return = opt.process(args)
            assert opt.value == val_exp
            assert process_return == return_args

    def test_unused(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("-a",),
            neg_triggers=(),
            prefix="",
        )
        with pytest.raises(ParameterError):
            opt.value

    def test_too_few_args(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("-a",),
            neg_triggers=(),
            prefix="",
        )
        with pytest.raises(TriggerError):
            opt.process([])

    def test_multiple_bind(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            prefix="",
        )
        opt.process(["--yes"])
        assert opt.value is True

        opt.process(["--no"])
        assert opt.value is False

    def test_isinstance_option(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            prefix="",
        )
        assert isinstance(opt, Option)

    def test_isinstance_parameter(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            prefix="",
        )
        assert isinstance(opt, Parameter)

    def test_convert_argument(self):
        opt = bool_option(
            ParameterSignature(
                name="a",
                python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                cli_kind=CliParamKind.OPTION,
                descr="test",
                default_value=...,
                annot=bool,
            ),
            pos_triggers=("--yes",),
            neg_triggers=("--no",),
            prefix="",
        )
        with pytest.raises(Exception, match="Can't convert option to argument"):
            opt.to_argument()


class TestOption:
    @pytest.mark.parametrize(
        "triggers,prefix,args,return_args, val_exp",
        [
            (("--path", "-p"), "", ["--path", "/a/b"], [], Path("/a/b")),
            (("--path", "-p"), "", ["-p", "/a/b"], [], Path("/a/b")),
            (
                ("--path", "-p"),
                "",
                ["--path", "/a/b", "other"],
                ["other"],
                Path("/a/b"),
            ),
            (("--path", "-p"), "", ["-a", "/a/b"], [], TriggerError),
            (("--path", "-p"), "", ["--foo", "/a/b"], [], TriggerError),
            (("--path", "-p"), "group", ["--group-path", "/a/b"], [], Path("/a/b")),
            (
                ("--path", "-p"),
                "group",
                ["--path", "/a/b"],
                [],
                TriggerError,
            ),
            (("--path", "-p"), "group", ["-p", "/a/b"], [], TriggerError),
            (
                ("--path", "-p"),
                "group",
                ["--group-path", "/a/b", "other"],
                ["other"],
                Path("/a/b"),
            ),
            (("--path", "-p"), "group", ["-a", "/a/b"], [], TriggerError),
            (
                ("--path", "-p"),
                "group",
                ["--foo", "/a/b"],
                [],
                TriggerError,
            ),
        ],
    )
    def test_normal(self, triggers, prefix, args, return_args, val_exp):
        """Test that BoolOption works as expected."""

        opt = Option(
            **asdict(
                ParameterSignature(
                    name="a",
                    python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    cli_kind=CliParamKind.OPTION,
                    descr="Path option",
                    default_value=...,
                    annot=Path,
                )
            ),
            processors=[
                ConvertOnceTriggerProcessor(
                    triggers=triggers,
                    res_type=Path,
                    type_converter=PathCLIArgConverter(Path),
                )
            ],
            prefix=prefix,
        )
        if type(val_exp) == type and issubclass(val_exp, Exception):
            # raises an error
            with pytest.raises(val_exp):
                opt.process(args)
        else:
            process_return = opt.process(args)
            assert opt.value == val_exp
            assert process_return == return_args

    def test_too_few_args(self):
        opt = Option(
            **asdict(
                ParameterSignature(
                    name="a",
                    python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    cli_kind=CliParamKind.OPTION,
                    descr="Path option",
                    default_value=[],
                    annot=Path,
                )
            ),
            processors=[
                ConvertOnceTriggerProcessor(
                    triggers=("--path", "-p"),
                    res_type=Path,
                    type_converter=PathCLIArgConverter(Path),
                )
            ],
        )
        with pytest.raises(TooFewArgsError):
            opt.process(["--path"])
            opt.value

    def test_path_opt_multi(self, store):
        opt = Option(
            **asdict(
                ParameterSignature(
                    name="a",
                    python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    cli_kind=CliParamKind.OPTION,
                    descr="Path option",
                    default_value=[],
                    annot=Path,
                )
            ),
            processors=[
                ConvertListTriggerProcessor(
                    triggers=("--path", "-p"),
                    res_type=Path,
                    type_converter=PathCLIArgConverter(Path),
                )
            ],
        )
        opt.process(["--path", "/a/b"])
        opt.process(["--path", "/c"])
        assert opt.value == [Path("/a/b"), Path("/c")]

    def test_path_to_argument(self, store):
        opt = Option(
            **asdict(
                ParameterSignature(
                    name="a",
                    python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    cli_kind=CliParamKind.OPTION,
                    descr="Path option",
                    default_value=[],
                    annot=Path,
                )
            ),
            processors=[
                ConvertListTriggerProcessor(
                    triggers=("--path", "-p"),
                    res_type=Path,
                    type_converter=PathCLIArgConverter(Path),
                )
            ],
        )

        arg = opt.to_argument()

        arg.process(["/a/b", "/c"])
        assert arg.value == [Path("/a/b"), Path("/c")]


class TestArgument:
    def path_arg(self) -> Argument:
        arg = Argument(
            **asdict(
                ParameterSignature(
                    name="a",
                    python_kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    cli_kind=CliParamKind.OPTION,
                    descr="Path option",
                    default_value=...,
                    annot=Path,
                )
            ),
            type_converter=PathCLIArgConverter(Path),
            res_type=Path,
        )
        return arg

    def test_path_arg(self):
        path_arg = self.path_arg()
        path_arg.process(["/a/b"])
        assert path_arg.value == Path("/a/b")


class TestParamGroup:
    def param_group(self) -> ParameterGroup:
        res = process_class_to_param_group(
            NestedClass, config=Config(), name="test", prefix_this="", python_kind=None
        )
        res.default_value = NestedClass(a=1)
        return res

    def test_default(self):
        param_group = self.param_group()
        assert param_group.value == NestedClass(a=1)

    def test_single_incomplete_bind(self):
        param_group = self.param_group()
        param_group.process(["--b", "test2"])
        with pytest.raises(ParameterError):
            param_group.value

    def test_single_complete_bind(self):
        param_group = self.param_group()
        param_group.process(["--a", "2"])
        assert param_group.value == NestedClass(a=2)

    def test_both_bind(self):
        param_group = self.param_group()
        param_group.process(["--a", "2"])
        param_group.process(["--b", "test2"])
        assert param_group.value == NestedClass(a=2, b="test2")
