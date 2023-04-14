"""WIP: pydantic datamodels with some of the functionality"""
import datetime
import json
import pathlib
from typing import List, Union

import pydantic

# Custom pydantic types


class StrToList:
    """Helper class to force strings to list of strings."""

    @classmethod
    def __get_validators__(cls):
        yield cls.str_to_list

    @staticmethod
    def str_to_list(item):
        if isinstance(item, str):
            return [item]

        raise TypeError("str type expected")


class DataDownload:
    """Helper class to convert path to DataDownload like structure."""

    # NOTE: functionality should likely be in the adapter class / registration functions, in which
    # we could handle also other downloadable data creation like in entity-management. This could
    # become a mere subclass of it for config files.

    @classmethod
    def __get_validators__(cls):
        yield cls.wrap

    @staticmethod
    def wrap(path):
        from bluepyentity.register import _wrap_linked_file_path

        if isinstance(path, str):
            return {"type": "DataDownload", "url": _wrap_linked_file_path(path)}

        raise TypeError("str type expected")


ListOfStr = Union[StrToList, List[str]]


# Data Models


class BaseModel(pydantic.BaseModel):

    type: str = None

    class Config:

        extra = pydantic.Extra.allow
        arbitrary_types_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.type or self.__class__.__name__

    @classmethod
    def parse_obj(cls, dict_):
        # If we wish to have a class that would automatically solve id's during creation of the model
        # we can extend the parse_obj functionality. E.g., in an adapter class between the
        # kgforge.Resource and the pydantic models here.

        r = super().parse_obj(dict_)
        print("GET AND OVERWRITE THE ID FIELDS HERE")
        return r

    @classmethod
    def from_dict(cls, dict_):
        """Create class from dict."""
        # Could as well be from file
        return cls.parse_obj(dict_)

    @classmethod
    def get_id_fields(cls):
        """Gather ID fields of all the inherited classes."""
        id_fields = [getattr(subcls, "_id_fields", set()) for subcls in cls.__mro__]
        return set().union(*id_fields)

    def to_dict(self):
        # Using json to recursively change all subclasses to dicts as well.
        return json.loads(self.json())


class EntityMixIn(BaseModel):

    wasAttributedTo: str = None
    wasGeneratedBy: str = None
    wasDerivedFrom: str = None
    dateCreated: datetime.datetime = None

    _id_fields = {
        "wasAttributedTo",
        "wasGeneratedBy",
        "wasDerivedFrom",
    }


class Entity(EntityMixIn):

    id: str = None
    name: str = None
    description: str = None
    distribution: List[str] = None


class Activity(BaseModel):
    name: str = None
    status: str = None  # Pending/Running,Done/Failed
    used: str = None
    generated: str = None
    startedAtTime: str = None
    endedAtTime: str = None
    wasStartedBy: str = None
    wasInformedBy: str = None
    wasInfluencedBy: str = None

    _id_fields = {
        "used",
        "generated",
        "wasStartedBy",
        "wasInformedBy",
        "wasInfluencedBy",
    }


class AnalysisReport(Entity):
    image: ListOfStr = None

    # Added
    derivation: str = None
    types: ListOfStr = None


# Should likely need a specific handling to fetch and include the "notation" field
class BrainLocation(BaseModel):
    pass


class ModelInstance(Entity):
    modelOf: str = None
    brainLocation: BrainLocation = None
    subject: str = None

    _id_fields = {
        "subject",
    }


# CIRCUIT


class DetailedCircuit(ModelInstance):
    circuitConfigPath: DataDownload
    circuitType: str = None

    # These should be removed?
    circuitBase: str = None
    nodeCollection: str = None
    edgeCollection: str = None
    target: str = None

    # Added
    atlasRelease: str = None

    _id_fields = {
        "atlasRelease",
    }


class DetailedCircuitValidation(Activity):
    pass


class DetailedCircuitValidationReport(AnalysisReport):
    pass

    # SIMULATION


class Simulation(Activity):
    spikes: None
    jobId: None
    path: None
    params: None

    # Added
    simulationConfigPath: None

    _id_fields = {
        "spikes",
    }


class SimulationCampaignGeneration(Activity):
    pass


class SimulationConfiguration(Entity):
    circuit: str = None

    _id_fields = {
        "circuit",
    }


class SimulationCampaignConfiguration(Entity):
    configuration: pathlib.Path = None
    template: pathlib.Path = None
    target: pathlib.Path = None


class EModelScript(Entity):
    etype_annotation_id: str = None
    iteration_tag: str = None
    holding_current: str = None
    threshold_current: str = None

    _id_fields = {
        "etype_annotation_id",
    }
