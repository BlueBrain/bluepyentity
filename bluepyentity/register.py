"""Tools to register resources in Nexus."""
import logging
import re
import sys
from abc import ABC, abstractmethod

import kgforge

from bluepyentity import utils

L = logging.getLogger(__name__)

FILE_URI = "file://"
RE_URL = re.compile("^http(s)?://")
RE_NOT_FILE_URI = re.compile(f"^(?!{FILE_URI})")
MODULE = sys.modules[__name__]


def _is_url(item):
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
    """Base class for resources to register."""

    required = {}
    possible_ids = {}

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
                f"'{self._forge._store.bucket}' "  # pylint: disable=protected-access
                f"with an id of: '{existing.id}'"
            )

        with utils.silence_stdout():
            self._forge.register(self.resource)

        # KnowledgeGraphForge(debug=True) does not make register raise (see: DKE-1065)
        if self.resource._last_action.succeeded:  # pylint: disable=protected-access
            return

        raise RuntimeError(self.resource._last_action.message)  # pylint: disable=protected-access

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
        """Format needed values in the definition."""

    def _find_existing(self):
        """Find resource matching the definition in Nexus."""
        found = self._forge.search({"type": self.type}, cross_bucket=True)
        for r in found:
            if self._is_equal_to_nexus_resource(r):
                return r

        return None

    def _get_distribution(self):
        """Create a distribution of files to be uploaded."""
        return [self._forge.attach(path) for path in self._definition.get("upload", [])]

    def _is_equal_to_nexus_resource(self, resource):
        """Implements checking if the definition is equal to a nexus resource."""
        return getattr(self.resource, "id", None) == resource.id

    def _with_defaults(self, definition):
        """Add default values to definiton."""
        defaults = utils.get_default_params(self.type)
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

    def _is_equal_to_nexus_resource(self, resource):
        """Checks equality assuming two simulations are the same if they have same config."""
        url = utils.traverse_attributes(resource, ["simulationConfigPath", "url"])

        return self.resource.simulationConfigPath.url == url


class AnalysisReport(Resource):
    """Class to register resources of type AnalysisReport."""

    # New format of AnalysisReport like in:
    # https://staging.nise.bbp.epfl.ch/nexus/v1/resources/bbp_test/studio_data_11/_/877ac166-779c-4926-9473-cca6bee0f50b
    required = {"configuration"}

    def _create_resource(self):
        self._check_required()
        definition = self.definition
        configuration = self._forge.retrieve(definition.pop("configuration"), cross_bucket=True)
        images = definition.pop("images", [])

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

    def _format_attributes(self, definition):
        """Nothing to do currently."""
        return definition


class DetailedCircuitValidationReport(AnalysisReport):
    """Class to register resources of type DetailedCircuitValidationReport."""

    # Currently the definition seems the same as for AnalysisReport


class SimulationCampaignConfiguration(Resource):
    """Class to register resources of type SimulationCampaignConfiguration."""

    required = {"configuration", "template"}
    possible_ids = {"wasGeneratedBy"}

    def _format_attributes(self, definition):
        patch = {}
        for attr in ("configuration", "target", "template"):
            if (path := definition.get(attr)) is not None:
                patch[attr] = self._forge.attach(path)

        return dict(definition, **patch)


def register(forge, resource_def, dry_run=False):
    """Register a Resource in Nexus.

    The parameters of the resource are given in a file.

    Args:
        forge (kgforge.core.KnowledgeGraphForge): nexus-forge instance.
        resource_def (str): Path to the YAML or JSON file.
        dry_run (bool): Do not register but print the parsed resource.
    """
    resource_dict = utils.parse_dict_from_file(resource_def)
    res_type = resource_dict.get("type", None)

    if cls := getattr(MODULE, res_type, None):
        resource = cls(resource_dict, forge)
    else:
        raise NotImplementedError(f"Unsupported type: '{res_type}'")

    if dry_run:
        # Log w/ critical level to ensure always being printed
        L.critical("%s:\n%s", res_type, resource.resource)
        return

    resource.register()
    L.info("'%s' successfully registered with id: '%s'", res_type, resource.resource.id)
