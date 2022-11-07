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
            # TODO: decide on action to take
            L.warning(e.args[0])
    elif isinstance(id_, list):
        return [_wrap_id_fetch(i, forge) for i in id_]

    return id_


# NOTE: Should this work with bluepyentity.nexus.entityEntity?
class Resource(ABC):
    required = {}
    possible_ids = {}

    def __init__(self, definition, forge):
        # TODO: add registration to em.nexus.connector.Connector and use that instead of using
        # kgforge methods directly
        self._definition = definition
        self._forge = forge
        self._resource = self._create_resource()

    @property
    def definition(self):
        """Adds defaults to the given definition and wraps the items in Nexus format."""
        refined = self._format_attributes(self._definition)
        refined = self._wrap_fields_with_ids(refined)

        # Fields to not store in Nexus
        refined.pop("upload", None)
        refined.pop("brainRegion", None)

        return self._with_defaults(refined)

    @property
    def resource(self):
        """Access the resource."""
        return self._resource

    @property
    def type(self):
        """Return the Nexus type of the resource."""
        return self._definition["type"]

    def register(self):
        """Register the resource in Nexus."""
        if existing := self._find_existing():
            raise RuntimeError(
                f"Similar '{self.type}' definition already exists in project "
                f"'{self._forge._store.bucket}' with an id of: '{existing.id}'"
            )
        else:
            with em.utils.silence_stdout():
                self._forge.register(self.resource)

            # KnowledgeGraphForge(debug=True) does not make register raise (see: DKE-1065)
            if self.resource._last_action.succeeded:
                return

            raise RuntimeError(self.resource._last_action.message)

    def _get_distribution(self):
        """Create a distribution of files to be uploaded."""
        return [self._forge.attach(path) for path in self._definition.get("upload", [])]

    def _check_required(self):
        """Check that the required items are defined."""
        missing = self.required - set(self._definition)
        assert not missing, f"Missing attributes: {missing}"

    def _create_resource(self):
        """Create a kgforge Resource of the definition."""
        self._check_required()
        resource = kgforge.core.Resource.from_json(self.definition)

        if distribution := self._get_distribution():
            setattr(resource, "distribution", distribution)

        return resource

    @abstractmethod
    def _format_attributes(self, definition):
        """If needed, format certain values in the definition."""

    def _find_existing(self):
        """Find resource matching the definition in Nexus."""
        found = self._forge.search({"type": self.type}, cross_bucket=True)
        for r in found:
            if self._is_equal(r):
                return r

        return None

    @abstractmethod
    def _is_equal(self, resource):
        """Implements checking if the definition is equal to a nexus resource."""

    def _with_defaults(self, definition):
        """Add default values to definiton."""
        defaults = em.utils.get_default_params(self.type)
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
    required = {"name", "description", "circuitConfigPath", "circuitType"}
    possible_ids = {"wasGeneratedBy"}

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
            brain_region = self._forge.reshape(brain_region, ["id", "label"])
            patch["brainLocation"] = {
                "type": "BrainLocation",
                "brainRegion": brain_region,
            }

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
            patch["simulationConfigPath"] = {
                "type": "DataDownload",
                "url": _wrap_linked_file_path(path),
            }

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
    # Should be added to the environments.py but using this here for now to not break anything
    forge._debug = True

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
