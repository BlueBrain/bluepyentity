import re
from unittest.mock import Mock, patch

import pytest

import bluepyentity.entity_definitions
import bluepyentity.register as test_module
from bluepyentity.exceptions import BluepyEntityError


def test__get_schema_id():
    forge = Mock(_model=Mock(schema_id=Mock(side_effect=ValueError("test_error"))))
    entity = Mock(get_schema_type=Mock(return_value="test_type"))
    assert test_module._get_schema_id(forge, entity) is None


def test__get_class_by_name():
    expected = bluepyentity.entity_definitions.DetailedCircuit
    assert test_module._get_class_by_name("DetailedCircuit") == expected

    with pytest.raises(NotImplementedError, match="Entity type not implemented"):
        test_module._get_class_by_name("no_such_class")


def test__resolve_class_from_list():
    expected = bluepyentity.entity_definitions.DetailedCircuitValidationReport
    class_names = ["DetailedCircuitValidationReport", "Entity", "AnalysisReport"]
    assert test_module._resolve_class_from_list(class_names) == expected

    expected = bluepyentity.entity_definitions.DetailedCircuit
    class_names = ["Entity", "DetailedCircuit"]
    assert test_module._resolve_class_from_list(class_names) == expected

    with pytest.raises(
        BluepyEntityError,
        match="All the types .* need to exist in the same chain of inheritance",
    ):
        test_module._resolve_class_from_list(["Entity", "Simulation", "DetailedCircuit"])


def test__parse_definition():
    res = test_module.parse_definition({"type": "Entity"})
    assert isinstance(res, bluepyentity.entity_definitions.Entity)

    res = test_module.parse_definition({"type": ["Entity", "AnalysisReport"]})
    assert isinstance(res, bluepyentity.entity_definitions.AnalysisReport)

    with (
        patch("bluepyentity.entity_definitions.get_type", Mock(return_value={})),
        pytest.raises(BluepyEntityError, match="Incorrect type for 'type'"),
    ):
        res = test_module.parse_definition({})


def test_register():
    forge = Mock(register=Mock())
    entity = Mock(to_resource=Mock(return_value="test"))

    res = test_module.register(forge, entity, dry_run=True, validate=False)
    entity.to_resource.assert_called_once_with(forge)
    forge.register.assert_not_called()
    assert res == "test"

    with patch(test_module.__name__ + "._get_schema_id") as patched:
        test_module.register(forge, entity, dry_run=True, validate=True)
        patched.assert_not_called()

    resource = Mock(_last_action=Mock(succeeded=True))
    entity = Mock(to_resource=Mock(return_value=resource))

    with patch(test_module.__name__ + "._get_schema_id") as patched:
        res = test_module.register(forge, entity, dry_run=False, validate=False)
        forge.register.assert_called_once_with(res, schema_id=None)
        patched.assert_not_called()
        assert res == resource

    with patch(test_module.__name__ + "._get_schema_id", Mock(return_value="test")) as patched:
        forge.register.reset_mock()
        test_module.register(forge, entity, dry_run=False, validate=True)
        patched.assert_called_once_with(forge, entity)
        forge.register.assert_called_once_with(res, schema_id="test")

    resource = Mock(_last_action=Mock(succeeded=False, message="epic fail"))
    entity = Mock(to_resource=Mock(return_value=resource))
    with pytest.raises(BluepyEntityError, match="Failed to register resource: epic fail"):
        test_module.register(forge, entity, dry_run=False, validate=False)
