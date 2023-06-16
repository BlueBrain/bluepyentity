import json
from unittest.mock import Mock, patch

import pytest
import yaml

import bluepyentity.utils as test_module
from bluepyentity.exceptions import BluepyEntityError


def test_silence_stdout(capfd):
    print("test")
    out, _ = capfd.readouterr()
    assert out == "test\n"

    with test_module.silence_stdout():
        print("test")
        out, _ = capfd.readouterr()
        assert out == ""


def test_forge_retrieve():
    forge = Mock(retrieve=Mock(return_value="test"))

    res = test_module.forge_retrieve(forge, "test_id")
    assert res == "test"
    forge.retrieve.assert_called_once_with("test_id", cross_bucket=True)

    forge = Mock(retrieve=Mock(return_value=None))

    with pytest.raises(BluepyEntityError, match="Unable to find a resource with id: test_id"):
        res = test_module.forge_retrieve(forge, "test_id")

    forge.retrieve.assert_called_once_with("test_id", cross_bucket=True)


def test_read_file(tmp_path):
    expected = {
        "test_dict": {"test_key": "test_value"},
        "test_int": 42,
        "test_str": "str",
        "test_list": ["str", 42],
        "test_no_date_resolution": "1990-11-30 03:04:00",
    }
    yml_str = yaml.dump(expected, Dumper=yaml.Dumper)
    json_str = json.dumps(expected)

    yml_path = tmp_path / "test.yml"
    yaml_path = tmp_path / "test.yaml"
    json_path = tmp_path / "test.json"
    fail_path = tmp_path / "test.fail"

    yml_path.write_text(yml_str)
    yaml_path.write_text(yml_str)
    json_path.write_text(json_str)
    fail_path.write_text("")

    assert test_module.parse_file(yml_path) == expected
    assert test_module.parse_file(yaml_path) == expected
    assert test_module.parse_file(json_path) == expected

    with pytest.raises(BluepyEntityError, match="unknown file format"):
        test_module.parse_file(fail_path)
