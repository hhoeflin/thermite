import json

from attrs import asdict

from thermite.preset_config import PresetConfig, read_preset_config

config_a = PresetConfig(opts=[["--a", "a"], ["--b", "b"]], args=["c", "d"], cmds=None)
config_b = PresetConfig(opts=[["--b", "b"], ["--d", "d"]], args=["c", "d"], cmds=None)
config_nested = PresetConfig(
    opts=[["--b", "b"], ["--d", "d"]], args=["c", "d"], cmds=dict(config_a=config_a)
)


def test_preset_config(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(asdict(config_nested)))

    config_in = read_preset_config(config_file)

    assert config_in == config_nested


def test_dict_preset_config(tmp_path):
    config_file = tmp_path / "config.json"
    obj = dict(config_a=asdict(config_a), config_nested=asdict(config_nested))
    config_file.write_text(json.dumps(obj))

    config_in = read_preset_config(config_file)

    assert config_in == dict(config_a=config_a, config_nested=config_nested)
