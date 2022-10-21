import logging
import re
from abc import ABC, abstractmethod

import kgforge

import bluepyentity as em

L = logging.getLogger(__name__)

FILE_URI = "file://"
RE_URL = re.compile("^http(s)?://")
RE_NOT_FILE_URI = re.compile(f"^(?!{FILE_URI})")


def _is_url(item):
    # NOTE: perhaps check for NEXUS URLs only
    return isinstance(item, str) and RE_URL.match(item)


def _wrap_file_path(path):
    return RE_NOT_FILE_URI.sub(FILE_URI, path)


def _wrap_id(id_, type_):
    return {"type": type_, "id": id_}


def _wrap_id_fetch(id_, forge):
    if _is_url(id_):
        nexus_resource = forge.retrieve(id_)

        if nexus_resource is not None:
            return _wrap_id(id_, nexus_resource.type)
    elif isinstance(id_, list):
        return [_wrap_id_fetch(i, forge) for i in id_]

    # TODO: decide on action, if resource is not found:
    # - no wrapping, return as is
    # - raise exception - stricter
    return id_


# NOTE: Should this work with bluepyentity.nexus.entityEntity?
class Resource(ABC):
    required = {}
    possible_ids = {}

    def __init__(self, definition, forge):
        self._definition = definition
        self._forge = forge
        self._resource = self._create_resource()

    @property
    def definition(self):
        refined = self._format_attributes(self._definition)
        refined = self._wrap_fields_with_ids(refined)
        return self._with_defaults(refined)

    @property
    def resource(self):
        return self._resource

    @property
    def type(self):
        return self._definition["type"]

    def register(self):
        if existing := self._find_existing():
            raise RuntimeError(
                f"Similar '{self.type}' definition already exists in project "
                f"'{self._forge._store.bucket}' with an id of: '{existing.id}'"
            )
        else:
            # TODO: how to silence forge's output?
            self._forge.register(self.resource)

            if self.resource._last_action.succeeded:
                return

            # TODO: debug
            # ValueError: Object of type datetime is not JSON serializable
            # w/ startedAtTime & endedAtTime
            raise RuntimeError(self.resource._last_action.message)

    def _check_required(self):
        missing = self.required - set(self._definition)
        assert not missing, f"Missing attributes: {missing}"

    def _create_resource(self):
        self._check_required()
        return kgforge.core.Resource.from_json(self.definition)

    @abstractmethod
    def _format_attributes(self, definition):
        """If needed, format certain values in the definition."""

    def _find_existing(self):
        found = self._forge.search({"type": self.type})
        for r in found:
            if self._is_equal(r):
                return r

        return None

    @abstractmethod
    def _is_equal(self, resource):
        """Implements checking if the definition is equal to a nexus resource."""

    def _with_defaults(self, definition):
        defaults = em.utils.get_default_params(self.type)
        return dict(defaults, **definition)

    def _wrap_fields_with_ids(self, definition):
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
    required = {"name", "description", "circuitConfigPath", "circuitType"}
    possible_ids = {"wasGeneratedBy"}

    def _format_attributes(self, definition):
        patch = {}
        path = definition["circuitConfigPath"]

        # NOTE: Does it need to be DataDownload, can it be just a URL as a string?
        if isinstance(path, str):
            patch["circuitConfigPath"] = {"type": "DataDownload", "url": _wrap_file_path(path)}

        return dict(definition, **patch)

    def _is_equal(self, resource):
        """Checks equality assuming two circuits are the same if they have same config."""

        # NOTE: Can't directly search based on circuitConfigPath, need to get all circuits and map
        # through them.
        url = em.utils.traverse_attributes(resource, ["circuitConfigPath", "url"])

        return self.resource.circuitConfigPath.url == url


class Simulation(Resource):
    required = {"name", "simulationConfigPath"}
    possible_ids = {"used"}

    def _format_attributes(self, definition):
        patch = {}
        path = definition["simulationConfigPath"]

        if isinstance(path, str):
            patch["simulationConfigPath"] = {"type": "DataDownload", "url": _wrap_file_path(path)}

        return dict(definition, **patch)

    def _is_equal(self, resource):
        """Checks equality assuming two simulations are the same if they have same config."""
        url = em.utils.traverse_attributes(resource, ["simulationConfigPath", "url"])

        return self.resource.simulationConfigPath.url == url


class Analysis(Resource):
    required = {}
    # Need to verify what different formats are we registering here
    # - Simulation / SimulationCampaign
    # - Analysis Report
    # - Circuit


def register(token, resource_def):
    """Register a Resource in Nexus.

    The parameters of the resource are given in a file.

    Args:
        token (str): NEXUS access token.
        resource_def (str): Path to the YAML or JSON file.
        project (str): target ORGANIZATION/PROJECT.
    """
    forge = em.environments.create_forge("prod", token, bucket="nse/test2")

    resource_dict = em.utils.parse_dict_from_file(resource_def)
    res_type = resource_dict.get("type", None)

    # TODO: initialize the classes dynamically
    if res_type == "DetailedCircuit":
        resource = DetailedCircuit(resource_dict, forge)
    elif res_type == "Simulation":
        resource = Simulation(resource_dict, forge)
    else:
        raise NotImplementedError(f"Unsupported type: '{res_type}'")

    resource.register()

    L.info(f"'{res_type}' successfully registered with id: '{resource.resource.id}'")
