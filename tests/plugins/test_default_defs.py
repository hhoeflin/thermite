import json

from attrs import asdict

from thermite.plugins.default_defs import DefaultDefs, read_default_defs

config_a = DefaultDefs(opts=[["--a", "a"], ["--b", "b"]], args=["c", "d"], cmds=None)
config_b = DefaultDefs(opts=[["--b", "b"], ["--d", "d"]], args=["c", "d"], cmds=None)
config_nested = DefaultDefs(
    opts=[["--b", "b"], ["--d", "d"]], args=["c", "d"], cmds=dict(config_a=config_a)
)


def test_default_defs(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(asdict(config_nested)))

    config_in = read_default_defs(config_file)

    assert config_in == config_nested


def test_dict_default_defs(tmp_path):
    config_file = tmp_path / "config.json"
    obj = dict(config_a=asdict(config_a), config_nested=asdict(config_nested))
    config_file.write_text(json.dumps(obj))

    config_in = read_default_defs(config_file)

    assert config_in == dict(config_a=config_a, config_nested=config_nested)
