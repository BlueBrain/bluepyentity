import pathlib
import re
from unittest.mock import MagicMock, Mock, patch

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


class TestDataDownload:
    def setup_method(self):
        self.test_obj = test_module.DataDownload()

    def test_validation(self):
        uri = "/absolute/path/to/file"
        expected = {"type": "DataDownload", "url": f"file://{uri}"}
        assert self.test_obj._custom_validator(uri) == expected

        uri = "./relative/path/file"
        abs_uri = str(pathlib.Path(uri).resolve())
        expected = {"type": "DataDownload", "url": f"file://{abs_uri}"}
        assert self.test_obj._custom_validator(uri) == expected

        for invalid in [1, {}, set(), [], tuple()]:
            with pytest.raises(TypeError, match="str type expected"):
                self.test_obj._custom_validator(invalid)


class TestListOfAccepted:
    def setup_method(self):
        self.test_cls = test_module.ListOfAccepted

    @pytest.mark.parametrize(
        "accepted, definition, expected",
        [
            ({str}, "test", ["test"]),
            ({str}, ["test"], ["test"]),
            ({str, int}, 1, [1]),
            ({str, int}, "test", ["test"]),
            ({str, int}, [1, "a", 2], [1, "a", 2]),
            ({str, int, float}, [1, "a", 2.0], [1, "a", 2.0]),
        ],
    )
    def test__as_list_of_accepted_types(self, accepted, definition, expected):
        assert self.test_cls._as_list_of_accepted_types(definition, accepted) == expected

        types = ", ".join(a.__name__ for a in accepted)
        err_msg = f"{types} or List[{types}] type expected"

        with pytest.raises(TypeError, match=re.escape(err_msg)):
            self.test_cls._as_list_of_accepted_types(item=None, accepted_types=accepted)

    def test__as_list_of_accepted_types_empty_list(self):
        with pytest.raises(TypeError, match=re.escape("str or List[str] type expected")):
            self.test_cls._as_list_of_accepted_types(item=[], accepted_types={str})


@pytest.mark.parametrize(
    "cls",
    [
        test_module.ListOfAccepted,
        test_module.ListOfStr,
        test_module.ListOfPath,
        test_module.DistributionConverter,
    ],
)
def test_validation_calls__as_list_of_accepted_types(cls):
    fun = Mock(return_value=[])

    class MockCls(cls):
        accepted = cls.accepted or {"str"}
        _as_list_of_accepted_types = fun

    MockCls._custom_validator("testing")

    fun.assert_called_once_with("testing", MockCls.accepted)


class TestListOfPath:
    def setup_method(self):
        self.test_cls = test_module.ListOfPath

    def test__custom_validator(self):
        assert self.test_cls._custom_validator("test") == [pathlib.Path("test")]
        assert self.test_cls._custom_validator(["test"]) == [pathlib.Path("test")]


class TestDistributionConverter:
    def setup_method(self):
        self.test_cls = test_module.DistributionConverter

    def test__custom_validator(self):
        expected = [{"path": "string"}]
        assert self.test_cls._custom_validator("string") == expected

        expected = [{"test": "value"}, {"path": "string"}]
        assert self.test_cls._custom_validator([{"test": "value"}, "string"]) == expected


class TestIDConverter:
    def setup_method(self):
        self.test_cls = test_module.IDConverter

    def test__custom_validator(self):
        expected = ["test"]
        res = self.test_cls._custom_validator("test")
        assert isinstance(res, test_module.ID)
        assert res.ids == expected

        res = self.test_cls._custom_validator(["test"])
        assert res.ids == expected

        # BaseModel.from_dict wraps the TypeError as BluepyEntityError
        with pytest.raises(BluepyEntityError, match=re.escape("str or List[str] type expected")):
            self.test_cls._custom_validator([1])


class TestBrainRegionConverter:
    def setup_method(self):
        self.test_cls = test_module.BrainRegionConverter

    def test__custom_validator(self):
        item = "test_string"
        res = self.test_cls._custom_validator(item)
        assert isinstance(res, test_module.BrainRegion)
        assert res.id == item

        res = self.test_cls._custom_validator({"id": item})
        assert isinstance(res, test_module.BrainRegion)
        assert res.id == item

        with pytest.raises(TypeError, match="str or dict type expected"):
            self.test_cls._custom_validator(1)

        # BaseModel.from_dict wraps the TypeError as BluepyEntityError
        with pytest.raises(BluepyEntityError, match="str type expected"):
            self.test_cls._custom_validator({"id": 1})


class TestBaseModel:
    def setup_method(self):
        self.test_cls = test_module.BaseModel

    def test_from_dict_error_handling(self):
        import pydantic

        class RaiseValidationError(pydantic.BaseModel):
            test_value: pydantic.StrictStr

        mock = lambda x: RaiseValidationError.parse_obj({"test_value": 42})
        with patch(f"{test_module.__name__}.BaseModel.parse_obj", mock):
            with pytest.raises(BluepyEntityError, match="str type expected"):
                self.test_cls.from_dict({})

    def test_get_formatted_definition(self):
        """Test that the childrens' `get_formatted_definition` is called recursively.
        Also test that recursion stops for children that does not have it."""
        wrap_ = lambda x: Mock(get_formatted_definition=x)
        mock_called = Mock(return_value={"b": "c"})
        mock_not_called = Mock()

        dict_ = {
            "a": wrap_(mock_called),
            "d": {
                # not called since "d" does not have get_formatted_definition
                "e": wrap_(mock_not_called),
            },
        }
        expected = {"a": {"b": "c"}, "d": {"e": dict_["d"]["e"]}}
        test_obj = self.test_cls.from_dict(dict_)

        res = test_obj.get_formatted_definition(forge="fake_forge")

        assert res == expected
        mock_not_called.assert_not_called()
        mock_called.assert_called_once_with("fake_forge")


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
