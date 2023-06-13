"""Tools to register resources in Nexus."""
import logging
import re

import kgforge

from bluepyentity import entity_definitions, utils
from bluepyentity.exceptions import BluepyEntityError

L = logging.getLogger(__name__)


def _get_schema_id(forge, entity):
    try:
        return forge._model.schema_id(entity.get_schema_type())  # pylint: disable=protected-access
    except ValueError:
        return None


def parse_definition(definition):
    type_ = entity_definitions.get_type(definition)
    classes = entity_definitions.get_registerable_classes()

    def _get_definition(class_):
        if class_ not in classes:
            raise NotImplementedError(f"Entity type not implemented: '{class_}'")

        return classes[class_]

    if isinstance(type_, str):
        cls = _get_definition(type_)
    elif isinstance(type_, list):
        classes_tuple = [_get_definition(str(class_)) for class_ in type_]
        for cls in classes_tuple:
            if all(issubclass(cls, cls_) for cls_ in classes_tuple):
                break
        else:
            raise BluepyEntityError(
                f"All the types {type_} need to exist in the same chain of inheritance."
            )
    else:
        # Added for clarity.  Workflow never reaches this point as pydantic raises.
        raise BluepyEntityError(f"Incorrect type for 'type': {type(type_).__name__}")

    return cls.from_dict(definition)


def register(forge, entity, dry_run=False, validate=False):
    """Used for testing. Does not really register anything."""
    resource = entity.to_resource(forge)

    if not dry_run:
        schema_id = _get_schema_id(forge, entity) if validate else None
        with utils.silence_stdout():
            forge.register(resource, schema_id=schema_id)

    action = resource._last_action  # pylint: disable=protected-access

    if action.succeeded:
        return resource

    raise BluepyEntityError(f"Failed to register resource: {action.message}")
