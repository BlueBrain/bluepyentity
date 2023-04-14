"""Tools to register resources in Nexus."""
import logging
import re
import sys
from functools import cached_property

import kgforge
import pkg_resources

from bluepyentity import utils

L = logging.getLogger(__name__)

FILE_URI = "file://"
RE_URL = re.compile("^http(s)?://")
RE_NOT_FILE_URI = re.compile(f"^(?!{FILE_URI})")
MODULE = sys.modules[__name__]

DEFAULT_PARAMS_PATH = pkg_resources.resource_filename(__name__, "default_params.yaml")
ENTITIES_PATH = pkg_resources.resource_filename(__name__, "entity_definitions.yaml")


def get_default_params(type_):
    """Get default parameters for given type.

    Args:
        type_ (str): type of resource

    Returns:
        dict: default parameters as dict
    """
    return utils.parse_dict_from_file(DEFAULT_PARAMS_PATH).get(type_, {})


def get_entity_definitions():
    """Get all known entities"""
    entities = utils.parse_dict_from_file(ENTITIES_PATH)
    skipped_entities = [
        "_Entity",
        "EntityMixin",
    ]
    for se in skipped_entities:
        if se in entities:
            del entities[se]
    return entities


def get_entity_definition(type_):
    """Get entity definition from the parsed definition file."""
    entities = utils.parse_dict_from_file(ENTITIES_PATH)

    def get_entity(name):
        ent_dict = entities[name].copy()
        ids = set(ent_dict.pop("_id_fields", []))

        for ent in ent_dict.pop("_inherits", []):
            inherited_ent, inherited_ids = get_entity(ent)
            ids.update(inherited_ids)
            ent_dict = dict(ent_dict, **inherited_ent)

        return ent_dict, ids

    if type_ in entities:
        schema, ids = get_entity(type_)
        return {"schema": schema, "ids": ids}

    return None


def _is_url(item):
    return isinstance(item, str) and RE_URL.match(item)


def _is_supported_type(type_):
    # This is a bit dangerous as the type can be _Entity which would evaluate as True here
    return get_entity_definition(type_) is not None


def _wrap_linked_file_path(path):
    """Wraps path as file URI if not already wrapped"""
    return RE_NOT_FILE_URI.sub(FILE_URI, path)


def _wrap_id(id_, type_):
    """Wrap Nexus ID to an object"""
    return {"type": type_, "id": id_}


def _wrap_id_fetch(id_, forge):
    """Find items with given IDs in Nexus and wrap them as objects."""
    if _is_url(id_):
        try:
            return _wrap_id(id_, forge.retrieve(id_, cross_bucket=True).type)
        except kgforge.core.commons.exceptions.RetrievalError as e:
            raise RuntimeError(e) from e
    elif isinstance(id_, list):
        return [_wrap_id_fetch(i, forge) for i in id_]

    return id_


# NOTE: Should this work with bluepyentity.nexus.entityEntity?
class Resource:
    """Base class for resources to register."""

    # This value should came from the schemas
    required = set()

    def __init__(self, definition, forge):
        """Resource initializer.

        Args:
            definition (dict): attributes and their values to register
            forge (kgforge.core.KnowledgeGraphForge): nexus-forge instance
        """
        # TODO: add registration to nexus.connector.Connector and use that instead of using
        # kgforge methods directly
        self._definition = definition
        self._forge = forge

        self._check_if_valid()

        self._resource = self._create_resource()

    @property
    def definition(self):
        """Adds defaults to the given definition and wraps the items in Nexus format."""
        refined = self._format_attributes(self._definition)
        refined = self._wrap_fields_with_ids(refined)

        # Fields to not store in Nexus
        refined.pop("brainRegion", None)

        return self._with_defaults(refined)

    @property
    def possible_ids(self):
        """Return the fields that possibly contains nexus ids"""
        return self._schema_definition["ids"]

    @property
    def resource(self):
        """Access the resource."""
        return self._resource

    @property
    def schema(self):
        """Schema for the entity."""
        # TODO: figure out how to get this from Nexus and use it to validate types etc.
        return self._schema_definition["schema"]

    @property
    def type(self):
        """Return the Nexus type of the resource."""
        return self._definition["type"]

    @cached_property
    def _schema_definition(self):
        return get_entity_definition(self.type)

    def register(self):
        """Register the resource in Nexus."""
        if existing := self._find_existing():
            bucket = self._forge._store.bucket  # pylint: disable=protected-access
            raise RuntimeError(
                f"Similar '{self.type}' definition already exists in project "
                f"'{bucket}' with an id of: '{existing.id}'"
            )

        try:
            schema_id = self._forge._model.schema_id(self.type)  # pylint: disable=protected-access
        except ValueError:
            schema_id = None

        try:
            self._forge.register(self.resource, schema_id=schema_id)
        except Exception as err:
            raise RuntimeError(err) from err

    def _check_if_valid(self):
        self._check_required()
        # NOTE: should this be removed, if schemas are handled by the backend?
        # Should extra attributes be allowed? Currently, the backend allows them.
        # self._check_schema()

    def _check_required(self):
        """Check that the required items are defined."""
        missing = self.required - set(self.definition)
        assert not missing, f"Missing attributes: {missing}"

    def _check_schema(self):
        disallowed = set(self.definition) - set(self.schema)
        disallowed -= {"type"}
        assert not disallowed, f"Disallowed attributes: {disallowed}"

    def _create_resource(self):
        """Create a kgforge Resource of the definition."""
        definition = self.definition
        definition["distribution"] = self._get_distribution()

        return kgforge.core.Resource.from_json(definition)

    def _format_attributes(self, definition):
        """Format needed values in the definition."""
        return definition

    def _find_existing(self):
        """Find resource matching the definition in Nexus."""
        found = self._forge.search({"type": self.type}, cross_bucket=True)
        for r in found:
            if self._is_equal_to_nexus_resource(r):
                return r

        return None

    def _get_distribution(self):
        """Create a distribution of files to be uploaded."""
        if distribution := self._definition.get("distribution"):
            assert isinstance(distribution, list)
            ret = []
            for path in distribution:
                if isinstance(path, dict):
                    resource = self._forge.attach(
                        path=path["path"], content_type=path["content_type"]
                    )
                else:
                    resource = self._forge.attach(path)
                ret.append(resource)
            return ret

        return None

    def _is_equal_to_nexus_resource(self, resource):
        """Implements checking if the definition is equal to a nexus resource."""
        return getattr(self.resource, "id", None) == resource.id

    def _with_defaults(self, definition):
        """Add default values to definiton."""
        defaults = get_default_params(self.type)
        return dict(defaults, **definition)

    def _wrap_fields_with_ids(self, definition):
        """Wrap attributes that contain IDs into objects."""
        patch = {}
        for field in self.possible_ids:
            value = definition.get(field)
            if isinstance(value, (str, list)):
                patch[field] = _wrap_id_fetch(value, self._forge)

        return dict(definition, **patch)

    # TODO:
    # - check if the definition conforms to expected schema/format
    # --- if from workflow, can we just expect it to?
    # --- how to activate this from nexus backend side or do we do it here?


class DetailedCircuit(Resource):
    """Class to register resources of type DetailedCircuit."""

    required = {"name", "description", "circuitConfigPath", "circuitType"}

    def _format_attributes(self, definition):
        patch = {}
        path = definition["circuitConfigPath"]

        # NOTE: Does it need to be DataDownload, can it be just a URL as a string?
        if isinstance(path, str):
            patch["circuitConfigPath"] = {
                "type": "DataDownload",
                "url": _wrap_linked_file_path(path),
            }

        # NOTE: perhaps better to do this lookup when creating the resource
        # Define brainLocation as suggested in DKE-1062
        if brain_region := definition.get("brainRegion"):
            brain_region = self._forge.retrieve(brain_region, cross_bucket=True)
            brain_region = self._forge.reshape(brain_region, ["id", "label", "notation"])
            patch["brainLocation"] = {
                "type": "BrainLocation",
                "brainRegion": brain_region,
            }

        return dict(definition, **patch)

    def _is_equal_to_nexus_resource(self, resource):
        """Checks equality assuming two circuits are the same if they have same config."""
        # NOTE: Can't directly search based on circuitConfigPath, need to get all circuits and map
        # through them.
        url = utils.traverse_attributes(resource, ["circuitConfigPath", "url"])

        return self.resource.circuitConfigPath.url == url


class Simulation(Resource):
    """Class to register resources of type Simulation."""

    # NOTE: If we have SimulationCampaigns, is this even needed?
    required = {"name", "simulationConfigPath"}

    def _format_attributes(self, definition):
        patch = {}
        path = definition["simulationConfigPath"]

        if isinstance(path, str):
            patch["simulationConfigPath"] = {
                "type": "DataDownload",
                "url": _wrap_linked_file_path(path),
            }

        return dict(definition, **patch)

    def _is_equal_to_nexus_resource(self, resource):
        """Checks equality assuming two simulations are the same if they have same config."""
        url = utils.traverse_attributes(resource, ["simulationConfigPath", "url"])

        return self.resource.simulationConfigPath.url == url


class AnalysisReport(Resource):
    """Class to register resources of type AnalysisReport."""

    # New format of AnalysisReport like in:
    # https://staging.nise.bbp.epfl.ch/nexus/v1/resources/bbp_test/studio_data_11/_/877ac166-779c-4926-9473-cca6bee0f50b
    required = {"derivation"}

    def _create_resource(self):
        definition = self.definition
        definition["distribution"] = self._get_distribution()
        configuration = self._forge.retrieve(definition.pop("derivation"), cross_bucket=True)
        images = definition.pop("image", [])

        # Needs to be Dataset, to have the same hasPart structure as in the example
        resource = kgforge.specializations.resources.Dataset.from_resource(
            self._forge, kgforge.core.Resource.from_json(definition)
        )

        resource.add_derivation(configuration)

        if not isinstance(images, list):
            images = [images]

        for path in images:
            resource.add_files(path)

        return resource


class DetailedCircuitValidationReport(AnalysisReport):
    """Class to register resources of type DetailedCircuitValidationReport."""

    # Currently the definition seems the same as for AnalysisReport


class SimulationCampaignConfiguration(Resource):
    """Class to register resources of type SimulationCampaignConfiguration."""

    required = {"configuration", "template"}

    def _format_attributes(self, definition):
        patch = {}
        for attr in ("configuration", "target", "template"):
            if (path := definition.get(attr)) is not None:
                patch[attr] = self._forge.attach(path)

        return dict(definition, **patch)


def register(forge, definition, dry_run=False):
    """Register a Resource in Nexus.

    The parameters of the resource are given in a file.

    Args:
        forge (kgforge.core.KnowledgeGraphForge): nexus-forge instance.
        definition(dict): Definition of the resource
        dry_run (bool): Do not register but print the parsed resource.
    """
    if "type" not in definition:
        raise NotImplementedError("Missing type")

    res_type = definition.get("type")

    if cls := getattr(MODULE, res_type, None):
        resource = cls(definition, forge)
    elif _is_supported_type(res_type):
        resource = Resource(definition, forge)
    else:
        raise NotImplementedError(f"Unsupported type: '{res_type}'")

    if not dry_run:
        resource.register()
        L.info("'%s' successfully registered with id: '%s'", res_type, resource.resource.id)

    return resource


# tested the below with yml files that use IDs to refer to existing resources. E.g.,
# ```
# type: DetailedCircuit
# atlasRelease: "https://bbp.epfl.ch/nexus/v1/resources/nse/test2/_/197d151d-4ed2-4549-85fd-6c51bd471262"
# brainLocation:
#     brainRegion:
#         id: "http://api.brain-map.org/api/v2/data/Structure/549"
#         label: Thalamus
# circuitConfigPath: /test/path
# circuitType: Test registration
# description: Test registration, to be deprecated, should validate
# name: Test Circuit registration
# wasGeneratedBy: "https://bbp.epfl.ch/nexus/v1/resources/nse/test2/_/9be40e75-8744-415b-b0b4-e4074ff54a8f"
# ```


class newResource:
    """Just an example of how this could work."""

    # NOTE:
    # Most of the functionality above would be unneeded as it would be handled in the definitions
    # or in an adapter class like this that should optimally spit out kgforge.Resource class that
    # would be ready to be registered or used by bluepyentity.nexus.entity.Entity

    # entity_definitions.py should handle:
    #  - input data type checking and structuring of data

    # this class should handle:
    # - anything that requires the forge instance (e.g., retrieving id fields)

    # If we introduce forge instance into the pydantic definitions, this class would become
    # obsolete. Not sure how much of functionality we want to build on those.

    def __init__(self, forge, definition):
        self._forge = forge
        self._definition = definition

    @property
    def resolved_id_fields(self):
        """Fetch and wrap the id fields."""
        res = {}
        for field in self._definition.get_id_fields():
            if id_ := getattr(self._definition, field, None):
                res[field] = _wrap_id_fetch(id_, self._forge)
        return res

    @property
    def ready_to_register(self):
        return dict(self._definition.to_dict(), **self.resolved_id_fields)


def register_pydantic(forge, definition, dry_run=False):
    """Used for testing. Does not really register anything."""
    # NOTE: this function should do only three things:
    # 1. create a kgforge.Resource with the help of a class like newResource above
    # 2. try to register the resource
    # 3. handle errors

    # All the other functionality should be done ith newResource like class and/or the
    # pydantic entity definitions in entity_definitions.py
    if "type" not in definition:
        raise NotImplementedError("Missing type")

    res_type = definition.get("type")

    from bluepyentity import entity_definitions

    cls = getattr(entity_definitions, res_type, None)

    if cls is not None:
        res = cls.from_dict(definition)
        item = newResource(forge, res)
        from pprint import pprint

        pprint(item.ready_to_register)
