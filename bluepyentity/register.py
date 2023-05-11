"""Tools to register resources in Nexus."""
import logging
import re

import kgforge

from bluepyentity import entity_definitions

L = logging.getLogger(__name__)


def _get_schema_id(forge, resource):
    try:
        return forge._model.schema_id(resource.type)  # pylint: disable=protected-access
    except ValueError:
        return None


def _parse_definition(definition):
    type_ = definition.get("type")
    classes = entity_definitions.get_registerable_classes()

    if not type_:
        raise RuntimeError("Definition is missing field: 'type'")

    if type_ not in classes:
        raise NotImplementedError(f"Entity type not implemented: '{type_}'")

    return classes[type_].from_dict(definition)


def register(forge, definition, dry_run=False, validate=False):
    """Used for testing. Does not really register anything."""
    entity = _parse_definition(definition)
    resource = entity.to_resource(forge)

    if not dry_run:
        schema_id = _get_schema_id(forge, resource) if validate else None
        forge.register(resource, schema_id=schema_id)

    return resource
