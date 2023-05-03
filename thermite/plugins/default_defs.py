"""Plugin to allow for setting of defaults via external json or yaml file."""
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Union

from attrs import field, mutable
from loguru import logger

from thermite.command import Command


@mutable
class DefaultDefs:
    """Holds the new default value settings."""

    opts: List[Union[str, List[str]]] = field(factory=list)
    args: Dict[str, Union[str, List[str]]] = field(factory=Dict)
    cmds: Dict[str, "DefaultDefs"] = field(factory=Dict)


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


def read_default_defs(file: Path):
    if file.suffix.lower() in [".json"]:
        import cattrs.preconf.json as cjson

        json_converter = DefaultDefsConverter(
            cjson.make_converter(forbid_extra_keys=True)
        )
        preset_conf = json_converter.structure(
            json.loads(file.read_text()), Union[Dict[str, DefaultDefs], DefaultDefs]
        )
        return preset_conf
    if file.suffix.lower() in [".yaml", "yml"]:
        import cattrs.preconf.pyyaml as cpyyaml

        yaml_converter = DefaultDefsConverter(
            cpyyaml.make_converter(forbid_extra_keys=True)
        )
        try:
            import yaml as pyyaml

            with file.open("rb") as f:
                preset_conf = yaml_converter.structure(
                    pyyaml.safe_load(f), Union[Dict[str, DefaultDefs], DefaultDefs]
                )
            return preset_conf
        except ImportError:
            pass
        try:
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")

            with file.open("rb") as f:
                preset_conf = yaml_converter.structure(
                    yaml.load(f), Union[Dict[str, DefaultDefs], DefaultDefs]
                )
            return preset_conf
        except ImportError:
            pass

        raise Exception(
            "When using yaml for preset configs, either pyyaml "
            "or ruamel.yaml have to be installed."
        )


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
        res = res.subcmds[elem]

    return res


@mutable
class SetNewDefaultCallback:
    default_defs: DefaultDefs

    def __call__(self, cmd: Command) -> Command:
        cmd_call_hierarachy = get_hierarchy(cmd)
        # we retrieve the appropriate subcmd
        subcmd_default_defs = retrieve_default_defs_subcmd(
            cmd_call_hierarachy, self.default_defs
        )
        # for processing we operate on a copy
        cmd_cpy = deepcopy(cmd)
        cmd.param_group
        return cmd
