"""Datamodels with some of the functionality"""
import datetime
import inspect
import pathlib
import re
import sys
from abc import ABC, abstractmethod
from typing import List, Literal, Union

import kgforge
import pydantic

from bluepyentity import utils
from bluepyentity.exceptions import BluepyEntityError

MODULE = sys.modules[__name__]

FILE_URI = "file://"
RE_URL = re.compile("^http(s)?://")
RE_NOT_FILE_URI = re.compile(f"^(?!{FILE_URI})")


def _wrap_file_uri(path):
    """Wraps path as file URI if not already wrapped"""
    return RE_NOT_FILE_URI.sub(FILE_URI, path)


def _is_url(item):
    return isinstance(item, str) and RE_URL.match(item)


def _fetch(id_, forge):
    """Fetch a resource or a list of resources."""
    if id_ is None:
        return None
    if _is_url(id_):
        return utils.forge_retrieve(forge, id_)
    if isinstance(id_, list):
        return [_fetch(i, forge) for i in id_]

    raise BluepyEntityError(f"Unsupported type: {type(id_)}")


# Converters


class Converter(ABC):
    """Converter class to convert data to expected format."""

    @classmethod
    def __get_validators__(cls):
        yield cls._custom_validator

    @staticmethod
    @abstractmethod
    def _custom_validator(item):
        """Validator function that also implements data conversion.

        Should return data in expected format or raise an exception."""


class DataDownload(Converter):
    """Helper class to convert path to DataDownload like structure."""

    @staticmethod
    def _custom_validator(item):
        if isinstance(item, str):
            return {"type": "DataDownload", "url": _wrap_file_uri(item)}

        raise TypeError("str type expected")


class ListOfAccepted(Converter, ABC):
    """Helper class to force accepted data types to list of those."""

    @property
    @abstractmethod
    def accepted(self):
        """Abstract class variable that should be a set of accepted types"""

    @staticmethod
    def _as_list_of_accepted_types(item, accepted_types):
        accepted = tuple(accepted_types)
        if isinstance(item, accepted):
            return [item]
        if isinstance(item, list) and all(isinstance(i, accepted) for i in item):
            return item

        classlist = ", ".join(a.__name__ for a in accepted)
        raise TypeError(f"{classlist} or List[{classlist}] type expected")

    @classmethod
    def _custom_validator(cls, item):
        return cls._as_list_of_accepted_types(item, cls.accepted)


class ListOfStr(ListOfAccepted):
    """Helper class to force strings to list of strings."""

    accepted = {str}


class ListOfPath(ListOfStr):
    """Helper class to force strings to list of Paths."""

    @classmethod
    def _custom_validator(cls, item):
        item = super()._custom_validator(item)
        return [Path(i) for i in item]


class DistributionConverter(ListOfAccepted):
    """Convert Distribution entries to expected format"""

    accepted = {str, dict}

    @classmethod
    def _custom_validator(cls, item):
        items = cls._as_list_of_accepted_types(item, cls.accepted)

        # item is already a dict or a str
        def _distribution_dict(item):
            return {"path": item} if isinstance(item, str) else item

        return [_distribution_dict(i) for i in items]


# Data Models


class BaseModel(pydantic.BaseModel):
    """Base model for the entities."""

    type: Union[str, ListOfStr] = None

    class Config:
        extra = pydantic.Extra.allow
        arbitrary_types_allowed = True

    @classmethod
    def from_dict(cls, dict_):
        """Create class from dict."""
        try:
            return cls.parse_obj(dict_)
        except pydantic.error_wrappers.ValidationError as e:
            raise BluepyEntityError(str(e)) from e

    def _get_elements_to_attach(self, *_):
        return {}

    def _attach_to_resource(self, *_):
        return

    def to_resource(self, forge):
        """Convert the definition to a nexus-forge resource."""
        definition = self.get_formatted_definition(forge)
        to_attach = self._get_elements_to_attach(definition)

        # Resource needs to be a Dataset for it to have methods such as add_derivation.
        resource = kgforge.core.Resource.from_json(definition)
        resource = kgforge.specializations.resources.Dataset.from_resource(forge, resource)

        self._attach_to_resource(forge, resource, to_attach)

        return resource

    def get_formatted_definition(self, forge):
        """Return the formatted definition."""
        res = {k: v for k, v in self.__dict__.items() if v is not None}

        for k, v in res.items():
            if hasattr(v, "get_formatted_definition"):
                res[k] = v.get_formatted_definition(forge)

        return res

    @classmethod
    def get_schema_type(cls):
        """Get type name for the schema."""
        return cls.__name__


class ID(BaseModel):
    ids: ListOfStr

    def get_formatted_definition(self, forge):
        def _wrap_id_fetch(id_):
            return {
                "id": id_,
                "type": _fetch(id_, forge).type,
            }

        ids = [_wrap_id_fetch(id_) for id_ in self.ids]

        return ids[0] if len(ids) == 1 else ids


class IDConverter(Converter):
    @classmethod
    def _custom_validator(cls, item):
        return ID.from_dict({"ids": item})


class EntityMixIn(BaseModel):
    wasAttributedTo: IDConverter = None
    wasGeneratedBy: IDConverter = None
    wasDerivedFrom: IDConverter = None
    dateCreated: datetime.datetime = None


class Entity(EntityMixIn):
    id: str = None
    name: str = None
    description: str = None
    distribution: DistributionConverter = None

    def _get_elements_to_attach(self, definition):
        return {"distribution": definition.pop("distribution", None)}

    def _attach_to_resource(self, forge, resource, to_attach):
        if to_attach["distribution"] is not None:
            for item in to_attach["distribution"]:
                resource.add_distribution(**item)


class Activity(BaseModel):
    name: str = None
    status: Literal["Pending", "Running", "Done", "Failed"] = None
    used: IDConverter = None
    generated: IDConverter = None
    startedAtTime: str = None
    endedAtTime: str = None
    wasStartedBy: IDConverter = None
    wasInformedBy: IDConverter = None
    wasInfluencedBy: IDConverter = None


class AnalysisReport(Entity):
    image: ListOfPath = None

    # Added
    derivation: IDConverter = None
    types: ListOfStr = None

    def _get_elements_to_attach(self, definition):
        to_attach = super()._get_elements_to_attach(definition)
        to_attach.update({k: definition.pop(k, None) for k in ("image", "derivation")})

        return to_attach

    def _attach_to_resource(self, forge, resource, to_attach):
        super()._attach_to_resource(forge, resource, to_attach)

        if to_attach["image"] is not None:
            for item in to_attach["image"]:
                resource.add_files(item)

        if to_attach["derivation"] is not None:
            derivation = _fetch(to_attach["derivation"], forge)
            resource.add_derivation(derivation)


class BrainRegion(BaseModel):
    id: str

    def get_formatted_definition(self, forge):
        return forge.reshape(_fetch(self.id, forge), ["id", "label", "notation"])


class BrainRegionConverter(Converter):
    @classmethod
    def _custom_validator(cls, item):
        if isinstance(item, str):
            item = {"id": item}
        if isinstance(item, dict):
            return BrainRegion.from_dict(item)

        raise TypeError("str or dict type expected")


class BrainLocation(BaseModel):
    brainRegion: BrainRegionConverter


class ModelInstance(Entity):
    modelOf: str = None
    brainLocation: BrainLocation = None
    subject: IDConverter = None


class DetailedCircuit(ModelInstance):
    circuitConfigPath: DataDownload
    circuitType: str = None

    # Added
    atlasRelease: IDConverter = None


class DetailedCircuitValidation(Activity):
    pass


class DetailedCircuitValidationReport(AnalysisReport):
    pass


class Simulation(Activity):
    spikes: IDConverter = None
    jobId: str = None
    path: pathlib.Path = None
    params: str = None

    # Added
    simulationConfigPath: DataDownload


class SimulationCampaignGeneration(Activity):
    pass


class SimulationConfiguration(Entity):
    circuit: IDConverter = None


class SimulationCampaignConfiguration(Entity):
    configuration: pathlib.Path = None
    template: pathlib.Path = None
    target: pathlib.Path = None

    def _get_elements_to_attach(self, definition):
        to_attach = super()._get_elements_to_attach(definition)
        to_attach.update(
            {k: definition.pop(k, None) for k in ("configuration", "template", "target")}
        )

        return to_attach

    def _attach_to_resource(self, forge, resource, to_attach):
        super()._attach_to_resource(forge, resource, to_attach)

        for file_key in ("configuration", "template", "target"):
            if to_attach[file_key] is not None:
                setattr(resource, file_key, forge.attach(path=to_attach[file_key]))


class EModelScript(Entity):
    etype_annotation_id: IDConverter = None
    iteration_tag: str = None
    holding_current: str = None
    threshold_current: str = None


def get_type(definition):
    """Get (and validate) the definition type."""
    try:
        type_ = BaseModel.parse_obj(definition).type
    except pydantic.error_wrappers.ValidationError as e:
        raise BluepyEntityError("'type' must be one of: str, List[str]") from e

    if type_ is None:
        raise BluepyEntityError("missing 'type' in definition")

    return type_


def _is_registerable(cls):
    non_registerable = {
        BaseModel,
        EntityMixIn,
        ID,
        ModelInstance,
    }

    return inspect.isclass(cls) and issubclass(cls, BaseModel) and cls not in non_registerable


def get_registerable_classes():
    """Fetch registerable classes as a dict."""
    return dict(inspect.getmembers(MODULE, _is_registerable))
