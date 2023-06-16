import re
from unittest.mock import Mock, patch

import pytest

import bluepyentity.entity_definitions as test_module
from bluepyentity.exceptions import BluepyEntityError


def test__wrap_file_uri():
    expected = "file://test"
    assert test_module._wrap_file_uri("test") == expected
    assert test_module._wrap_file_uri(expected) == expected


def test__is_url():
    assert test_module._is_url("http://test.com")
    assert test_module._is_url("https://test.com")
    assert not test_module._is_url("abc://test.com")
    assert not test_module._is_url(42)
    assert not test_module._is_url(None)


@patch("bluepyentity.utils.forge_retrieve", Mock(return_value="test"))
def test__fetch():
    assert test_module._fetch(id_=None, forge=None) is None
    assert test_module._fetch(id_="http://url.com", forge=None) == "test"
    assert test_module._fetch(id_=[None, None], forge=None) == [None, None]
    assert test_module._fetch(id_=["http://url.com"], forge=None) == ["test"]

    with pytest.raises(BluepyEntityError, match="Expected URL"):
        test_module._fetch(id_="url.com", forge=None)

    with pytest.raises(BluepyEntityError, match="Expected URL"):
        test_module._fetch(id_=Mock(), forge=None)


def test__is_registerable():
    assert not test_module._is_registerable("a")
    assert not test_module._is_registerable(str)
    assert not test_module._is_registerable(None)
    assert not test_module._is_registerable(test_module.BaseModel)
    assert test_module._is_registerable(test_module.DetailedCircuit)


def test_get_type():
    expected = "type_A"
    definition = {"type": expected}
    assert test_module.get_type(definition) == expected

    expected = ["type_A", "type_B"]
    definition = {"type": expected}
    assert test_module.get_type(definition) == expected

    with pytest.raises(BluepyEntityError, match=re.escape("'type' must be one of: str, List[str]")):
        test_module.get_type({"type": {"should": "fail"}})

    with pytest.raises(BluepyEntityError, match="missing 'type' in definition"):
        test_module.get_type({})


def test_get_registerable_classes():
    res = test_module.get_registerable_classes()
    assert all(issubclass(cls, test_module.BaseModel) for cls in res.values())
    assert not any(cls in res.values() for cls in test_module.NON_REGISTERABLE)
    assert all(res[k] == getattr(test_module, k) for k in res)
