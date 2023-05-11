"""Datamodels with some of the functionality"""
import datetime
import inspect
import pathlib
import re
import sys
from abc import ABC, abstractmethod
from typing import List, Literal

import kgforge
import pydantic

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
        return forge.retrieve(id_, cross_bucket=True)
    if isinstance(id_, list):
        return [_fetch(i, forge) for i in id_]

    raise RuntimeError(f"Unsupported type: {type(id_)}")


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

        classlist = ", ".join(accepted)
        raise TypeError(f"{classlist} or List[{classlist}] type expected")

    @classmethod
    def _custom_validator(cls, item):
        return cls._as_list_of_accepted_types(item, cls.accepted)


class ListOfStr(ListOfAccepted):
    """Helper class to force strings to list of strings."""

    accepted = {str}


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

    type: str = None

    class Config:

        extra = pydantic.Extra.allow
        arbitrary_types_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.type or self.__class__.__name__

    @classmethod
    def from_dict(cls, dict_):
        """Create class from dict."""
        # Could as well be from file
        return cls.parse_obj(dict_)

    def to_resource(self, forge):
        """Convert the definition to a nexus-forge resource."""
        data = self.get_formatted_definition(forge)

        # These need to be handled separately after creating the resource
        single_files = {"configuration", "template", "target"}
        all_special_cases = single_files.union({"derivation", "image", "distribution"})
        to_add = {k: data.pop(k, None) for k in all_special_cases}

        # Resource needs to be a Dataset for it to have methods such as add_derivation.
        resource = kgforge.core.Resource.from_json(data)
        resource = kgforge.specializations.resources.Dataset.from_resource(forge, resource)

        if to_add["derivation"] is not None:
            derivation = _fetch(to_add["derivation"], forge)
            resource.add_derivation(derivation)

        if to_add["image"] is not None:
            for item in to_add["image"]:
                resource.add_files(item)

        if to_add["distribution"] is not None:
            for item in to_add["distribution"]:
                resource.add_distribution(**item)

        for file_key in single_files:
            if to_add[file_key] is not None:
                setattr(resource, file_key, forge.attach(path=to_add[file_key]))

        return resource

    def get_formatted_definition(self, forge):
        """Return the formatted definition."""
        res = {k: v for k, v in self.__dict__.items() if v is not None}

        for k, v in res.items():
            if hasattr(v, "get_formatted_definition"):
                res[k] = v.get_formatted_definition(forge)

        return res


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
    image: ListOfStr = None

    # Added
    derivation: str = None
    types: ListOfStr = None


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

    # These should be removed?
    circuitBase: str = None
    nodeCollection: str = None
    edgeCollection: str = None
    target: str = None

    # Added
    atlasRelease: IDConverter = None


class DetailedCircuitValidation(Activity):
    pass


class DetailedCircuitValidationReport(AnalysisReport):
    pass


class Simulation(Activity):
    spikes: IDConverter = None
    jobId: str = None
    path: str = None
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


class EModelScript(Entity):
    etype_annotation_id: IDConverter = None
    iteration_tag: str = None
    holding_current: str = None
    threshold_current: str = None


# Functions to fetch registerable classes


def _is_registerable(cls):
    non_registerable = {
        BaseModel,
        Entity,
        EntityMixIn,
        ID,
        ModelInstance,
    }

    return inspect.isclass(cls) and issubclass(cls, BaseModel) and cls not in non_registerable


def get_registerable_classes():
    """Fetch registerable classes as a dict."""
    return dict(inspect.getmembers(MODULE, _is_registerable))
