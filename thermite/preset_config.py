import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import attrs


@attrs.mutable
class PresetConfig:
    args: Optional[List[str]] = None
    opts: Optional[List[List[str]]] = None
    cmds: Optional[Dict[str, "PresetConfig"]] = None


@attrs.mutable
class ConverterSetup:
    converter: Any

    def __attrs_post_init__(self):
        self.converter.register_structure_hook(PresetConfig, self.structure_preset)
        self.converter.register_structure_hook(
            Union[Dict[str, PresetConfig], PresetConfig], self.structure_preset_union
        )

    def structure_preset(self, val, obj_type):
        del obj_type
        if "cmds" in val and val["cmds"] is not None:
            for key in val["cmds"]:
                val["cmds"][key] = self.converter.structure(
                    val["cmds"][key], PresetConfig
                )

        return PresetConfig(**val)

    # we register an unstructuring hook for more complex type
    def structure_preset_union(self, val, obj_type):
        del obj_type
        if isinstance(val, dict):
            if set(val.keys()).issubset(set(["args", "opts", "cmds"])):
                # likely PresetConfig
                return self.converter.structure(val, PresetConfig)
            else:
                return self.converter.structure(val, Dict[str, PresetConfig])
        else:
            raise Exception("Can only structure dicts")

    def structure(self, val, klass):
        return self.converter.structure(val, klass)


def read_preset_config(file: Path):
    if file.suffix.lower() in [".json"]:
        import cattrs.preconf.json as cjson

        json_converter = ConverterSetup(cjson.make_converter(forbid_extra_keys=True))
        preset_conf = json_converter.structure(
            json.loads(file.read_text()), Union[Dict[str, PresetConfig], PresetConfig]
        )
        return preset_conf
    if file.suffix.lower() in [".yaml", "yml"]:
        import cattrs.preconf.pyyaml as cpyyaml

        yaml_converter = ConverterSetup(cpyyaml.make_converter(forbid_extra_keys=True))
        try:
            import yaml as pyyaml

            with file.open("rb") as f:
                preset_conf = yaml_converter.structure(
                    pyyaml.safe_load(f), Union[Dict[str, PresetConfig], PresetConfig]
                )
            return preset_conf
        except ImportError:
            pass
        try:
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")

            with file.open("rb") as f:
                preset_conf = yaml_converter.structure(
                    yaml.load(f), Union[Dict[str, PresetConfig], PresetConfig]
                )
            return preset_conf
        except ImportError:
            pass

        raise Exception(
            "When using yaml for preset configs, either pyyaml "
            "or ruamel.yaml have to be installed."
        )
