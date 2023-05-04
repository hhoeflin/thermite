"""Plugin to allow for setting of defaults via external json or yaml file."""
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Union

from attrs import field, mutable
from loguru import logger

from thermite.command import CliCallback, Command
from thermite.config import Event
from thermite.parameters import Argument, ParameterGroup


def make_list_of_str(x: Union[str, List[str]]) -> List[str]:
    if isinstance(x, str):
        return [x]
    else:
        return x


@mutable
class DefaultDefs:
    """Holds the new default value settings."""

    opts: List[Union[str, List[str]]] = field(factory=list)
    args: Dict[str, Union[str, List[str]]] = field(factory=dict)
    cmds: Dict[str, "DefaultDefs"] = field(factory=dict)

    def check(self):
        for opt in self.opts:
            opt = make_list_of_str(opt)
            assert opt[0].startswith("-")
            assert not any(x.startswith("-") for x in opt[1:])

        for cmd in self.cmds.values():
            cmd.check()


@mutable
class DefaultDefsConverter:
    """Converter using CAttrs to read PresetConfig from json/yaml."""

    converter: Any

    def __attrs_post_init__(self):
        self.converter.register_structure_hook(DefaultDefs, self.structure_defs)
        self.converter.register_structure_hook(
            Union[Dict[str, DefaultDefs], DefaultDefs], self.structure_defs_union
        )

    def structure_defs(self, val, obj_type):
        del obj_type
        if "cmds" in val and val["cmds"] is not None:
            for key in val["cmds"]:
                val["cmds"][key] = self.converter.structure(
                    val["cmds"][key], DefaultDefs
                )

        return DefaultDefs(**val)

    # we register an unstructuring hook for more complex type
    def structure_defs_union(self, val, obj_type):
        del obj_type
        if isinstance(val, dict):
            if set(val.keys()).issubset(set(["args", "opts", "cmds"])):
                # likely DefaultDefs
                return self.converter.structure(val, DefaultDefs)
            else:
                return self.converter.structure(val, Dict[str, DefaultDefs])
        else:
            raise Exception("Can only structure dicts")

    def structure(self, val, klass):
        return self.converter.structure(val, klass)


def read_default_defs(file: Path) -> Union[DefaultDefs, Dict[str, DefaultDefs]]:
    if file.suffix.lower() in [".json"]:
        import cattrs.preconf.json as cjson

        json_converter = DefaultDefsConverter(
            cjson.make_converter(forbid_extra_keys=True)
        )
        default_defs = json_converter.structure(
            json.loads(file.read_text()), Union[Dict[str, DefaultDefs], DefaultDefs]
        )
        return default_defs
    if file.suffix.lower() in [".yaml", ".yml"]:
        import cattrs.preconf.pyyaml as cpyyaml

        yaml_converter = DefaultDefsConverter(
            cpyyaml.make_converter(forbid_extra_keys=True)
        )
        try:
            import yaml as pyyaml

            with file.open("rb") as f:
                default_defs = yaml_converter.structure(
                    pyyaml.safe_load(f), Union[Dict[str, DefaultDefs], DefaultDefs]
                )
            return default_defs
        except ImportError:
            pass
        try:
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")

            with file.open("rb") as f:
                default_defs = yaml_converter.structure(
                    yaml.load(f), Union[Dict[str, DefaultDefs], DefaultDefs]
                )
            return default_defs
        except ImportError:
            pass

        raise Exception(
            "When using yaml for default definitions configs, either pyyaml "
            "or ruamel.yaml have to be installed."
        )
    else:
        raise Exception("Unknown file suffix {str(file)}")


def get_hierarchy(cmd: Command) -> List[str]:
    hierarchy: List[str] = []
    while cmd.prev_cmd is not None:
        prev_cmd = cmd.prev_cmd
        if len(prev_cmd._history) > 0:
            cmd_name = cmd.prev_cmd._history[-1]
            hierarchy.insert(0, cmd_name)
        else:
            logger.warning("History of previous command not recorded.")
        cmd = prev_cmd

    return hierarchy


def retrieve_default_defs_subcmd(hierarchy, default_defs: DefaultDefs) -> DefaultDefs:
    res = default_defs
    for elem in hierarchy:
        res = res.cmds[elem]

    return res


def transfer_values_to_defaults(
    value_pg: ParameterGroup, default_pg: ParameterGroup
) -> None:
    """Transfer the default value. It will be changed in-place."""
    import pudb

    pudb.set_trace()
    for name, param in value_pg.items():
        if isinstance(param, ParameterGroup):
            param_default = default_pg[name]
            assert isinstance(param_default, ParameterGroup)
            transfer_values_to_defaults(param, param_default)
        else:
            if not param.unset:
                try:
                    value = param.value
                    default_pg[name].default_value = value
                except Exception as e:
                    raise Exception(
                        f"In parameter {name} an error occured during "
                        "value retrieveal from default definition"
                    ) from e


@mutable
class ApplyDefaultsCommandCallback:
    default_defs: DefaultDefs

    def __attrs_post_init__(self):
        self.default_defs.check()

    def __call__(self, cmd: Command) -> Command:
        cmd_call_hierarachy = get_hierarchy(cmd)
        # we retrieve the appropriate subcmd
        subcmd_default_defs = retrieve_default_defs_subcmd(
            cmd_call_hierarachy, self.default_defs
        )

        # for processing we operate on a copy
        cmd_cpy = deepcopy(cmd)
        for opt_str_list in subcmd_default_defs.opts:
            input_args = make_list_of_str(opt_str_list)
            ret_args = cmd_cpy.param_group.process(input_args)
            if len(ret_args) > 0:
                raise Exception(
                    f"Option inputs {input_args} has leftover args {ret_args}"
                )
        for name, arg_str_list in subcmd_default_defs.args.items():
            arg_to_use = cmd_cpy.param_group[name]
            assert isinstance(arg_to_use, Argument)
            input_args = make_list_of_str(arg_str_list)
            ret_args = arg_to_use.process(input_args)
            if len(ret_args) > 0:
                raise Exception(
                    f"Argument {name} inputs {input_args} has leftover args {ret_args}"
                )

        # now we grab the outputs of these and put them in the place of the defaults
        transfer_values_to_defaults(cmd_cpy.param_group, cmd.param_group)
        return cmd


def read_default_defs_cb_func(cmd: Command, default_defs_path_str: str):
    # retrieve the default definitions we should use
    path_split = default_defs_path_str.split("#", maxsplit=1)
    if len(path_split) == 1:
        default_defs_path = Path(default_defs_path_str)
        default_defs = read_default_defs(default_defs_path)
        if not isinstance(default_defs, DefaultDefs):
            raise Exception(
                "When no subdefinition-name is given, the file has to"
                "consist of a single Definition"
            )
    else:
        default_defs_path = Path(path_split[0])
        subdefs_name = path_split[1]
        default_defs = read_default_defs(default_defs_path)
        if isinstance(default_defs, dict) and subdefs_name in default_defs:
            default_defs = default_defs[subdefs_name]
        else:
            raise Exception(
                f"No {subdefs_name} subdefinition found in {str(default_defs_path)}"
            )

    # now set the event at each command creation to adapt the defaults
    # also, for the current cmd it has to be applied here directly
    apply_defaults_cb = ApplyDefaultsCommandCallback(default_defs)
    apply_defaults_cb(cmd)
    cmd.config.event_callbacks.add_event_cb(
        event=Event.CMD_POST_CREATE, cb=apply_defaults_cb
    )


defaults_cli_callback = CliCallback(
    callback=read_default_defs_cb_func,
    triggers=["--defaults-file"],
    descr="Read defaults from file",
    num_req_args=1,
)

# TODO: Use START_ARGS_PRE_PROCESS event
