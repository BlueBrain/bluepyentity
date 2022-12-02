"""Materialization functions."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union

from kgforge.core import Resource

from bluepyentity.exceptions import BluepyEntityError
from bluepyentity.utils import without_file_prefix, write_json

L = logging.getLogger(__name__)


def materialize(
    forge, resource_id: str, output_file: Optional[Path] = None
) -> Dict[str, Dict[str, str]]:
    """Materialize a KG dataset with grouped data.

    Materialization generated a nested dictionary for each grouping level in the json dataset.

    Args:
        resource_id: Resource id.
        output_file: Optional output file to write the materialized dictionary.

    Returns:
        A nested dictionary of materialized entries.

    Example:
        {
            'mtypes': {
                'http://uri.interlex.org/base/ilx_0383198': {
                    'label': 'L23_BP',
                    'etypes': {
                        'http://uri.interlex.org/base/ilx_0738202': {
                            'label': 'dSTUT',
                            'path': 'L23_BP-DSTUT_densities_v3.nrrd'
                        }
                    }
                },
                'http://uri.interlex.org/base/ilx_0383202': {
                    'label': 'L23_LBC',
                    'etypes': {
                        'http://uri.interlex.org/base/ilx_0738200': {
                            'label': 'bSTUT',
                            'path': 'L23_LBC-BSTUT_densities_v3.nrrd'
                        },
                        'http://uri.interlex.org/base/ilx_0738198': {
                            'label': 'cSTUT',
                            'path': 'L23_LBC-CSTUT_densities_v3.nrrd'
                        }
                    }
                }
            }
        }
    """
    ontology_to_materializer = {
        "https://bbp.epfl.ch/ontologies/core/bmo/METypeDensity": materialize_me_type_densities,
    }

    resource = forge.retrieve(resource_id, cross_bucket=True)

    try:
        ontological_type = resource.about[0]
    except AttributeError as e:
        raise BluepyEntityError(
            f"Resource {resource_id} must have an 'about' entry with the ontological type."
        ) from e

    if ontological_type in ontology_to_materializer:

        materializer = ontology_to_materializer[ontological_type]
        return materializer(forge, resource_or_id=resource, output_file=output_file)

    raise BluepyEntityError(
        f"Ontological type {ontological_type} is not supported for materialization.\n"
        f"Supported types: {ontology_to_materializer}."
    )


def materialize_me_type_densities(
    forge, resource_or_id: Union[Resource, str], output_file: Optional[Path] = None
) -> Dict[str, Dict[str, str]]:
    """Materialize an me type density grouped dataset.

    Returns:
        A nested dictionary with two levels:
            1st level: Keys: MType identifiers, Values: EType groups corresponding to that MType
            2nd level: Keys: EType identifiers, Values: Dictionaries with path to me density.
    """
    resource = _get_resource(forge, resource_or_id)

    dataset = load_json_file_from_resource(resource)

    groups = {"mtypes": {}}
    for mtype_part in dataset["hasPart"]:

        mtype_id, mtype_label = mtype_part["@id"], mtype_part["label"]

        etype_groups = {}
        for etype_part in mtype_part["hasPart"]:

            etype_id, etype_label = etype_part["@id"], etype_part["label"]

            density_id = etype_part["hasPart"][0]["@id"]
            density_path = _get_density_resource_path(forge, density_id)

            etype_groups[etype_id] = {"label": etype_label, "path": density_path}

            L.debug("MType: %s, EType %s, Density Path: %s", mtype_label, etype_label, density_path)

        groups["mtypes"][mtype_id] = {"label": mtype_label, "etypes": etype_groups}

    if output_file:
        write_json(filepath=output_file, data=groups)

    return groups


def _get_resource(forge, resource_or_id: Union[Resource, str]):
    if isinstance(resource_or_id, Resource):
        return resource_or_id
    return forge.retrieve(resource_or_id, cross_bucket=True)


def _get_density_resource_path(forge, resource_id: str):

    density_resource = forge.retrieve(resource_id, cross_bucket=True)
    density_path = without_file_prefix(density_resource.distribution.atLocation.location)

    return density_path


def load_json_file_from_resource(resource):
    """Read json file from kg resource."""
    if isinstance(resource.distribution, list):
        assert len(resource.distribution) == 1
        distribution = resource.distribution[0]
    else:
        distribution = resource.distribution

    filepath = without_file_prefix(distribution.atLocation.location)

    return json.loads(Path(filepath).read_bytes())
