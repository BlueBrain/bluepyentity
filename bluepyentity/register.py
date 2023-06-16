"""Tools to register resources in Nexus."""
import logging
import re

import kgforge

from bluepyentity import entity_definitions, utils
from bluepyentity.exceptions import BluepyEntityError

CLASSES = entity_definitions.get_registerable_classes()
L = logging.getLogger(__name__)


def _get_schema_id(forge, entity):
    try:
        return forge._model.schema_id(entity.get_schema_type())  # pylint: disable=protected-access
    except ValueError:
        return None


def _get_class_by_name(class_name):
    if class_name not in CLASSES:
        raise NotImplementedError(f"Entity type not implemented: '{class_name}'")

    return CLASSES[class_name]


def _resolve_class_from_list(class_names):
    """Resolves the actual class from list of types."""
    classes = [_get_class_by_name(class_) for class_ in class_names]

    for cls in classes:
        if all(issubclass(cls, cls_) for cls_ in classes):
            return cls

    raise BluepyEntityError(
        f"All the types {class_names} need to exist in the same chain of inheritance."
    )


def parse_definition(definition):
    """Instantiates an entity based on definition."""
    type_ = entity_definitions.get_type(definition)

    if isinstance(type_, str):
        cls = _get_class_by_name(type_)
    elif isinstance(type_, list):
        cls = _resolve_class_from_list(type_)
    else:
        # Added for clarity.  Workflow never reaches this point as pydantic raises.
        raise BluepyEntityError(f"Incorrect type for 'type': {type(type_).__name__}")

    return cls.from_dict(definition)


def register(forge, entity, dry_run=False, validate=False):
    """Register the entity."""
    resource = entity.to_resource(forge)

    if not dry_run:
        schema_id = _get_schema_id(forge, entity) if validate else None
        with utils.silence_stdout():
            forge.register(resource, schema_id=schema_id)

        action = resource._last_action  # pylint: disable=protected-access

        if not action.succeeded:
            raise BluepyEntityError(f"Failed to register resource: {action.message}")

    return resource
