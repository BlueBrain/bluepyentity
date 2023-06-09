import tempfile
from copy import deepcopy
from pathlib import Path

from kgforge.core import Resource

from bluepyentity.utils import load_json, write_json


def clone_grouped_dataset_resource(forge_from, forge_to, resource: Resource) -> str:
    """Clone a resource with a json dataset between forge instances."""

    dataset = _load_json_from_distribution(resource.distribution)

    new_dataset = clone_grouped_dataset(forge_from, forge_to, dataset=dataset)

    new_resource = _copy_resource_metadata(forge_from, resource)

    with tempfile.TemporaryDirectory() as tdir:
        new_resource.distribution = _attach_json_dataset(
            forge=forge_to,
            dataset=new_dataset,
            path=Path(tdir, resource.distribution.name),
        )
        forge_to.register(new_resource)

    return new_resource


def _load_json_from_distribution(distribution):
    # TODO: Do not rely on gpfs path existence
    json_location = distribution.atLocation.location[7:]
    return load_json(json_location)


def _attach_json_dataset(forge, dataset, path):
    write_json(data=dataset, filepath=path)

    return forge.attach(path=path, content_type="application/json")


def _copy_resource_metadata(forge, resource: Resource) -> Resource:
    """Copy a resource's metadata without the store related information."""
    new_resource = Resource.from_json(forge.as_json(resource))
    del new_resource.id
    return new_resource


def clone_grouped_dataset(forge_from, forge_to, dataset: dict) -> dict:
    """ """
    already_migrated = {}

    def recursively_clone(d):
        if "hasPart" in d:
            d["hasPart"] = recursively_clone(d["hasPart"])
            return d

        if "@id" in d:
            resource_id = d["@id"]
            assert "rev" not in resource_id

            if "_rev" in d:
                resource_id = f"{resource_id}?rev={d['_rev']}"

            # re-use already migrated ids
            if resource_id in already_migrated:
                new_id = already_migrated[resource_id]
            else:
                new_id = _clone_resource(forge_from, forge_to, resource_id)
                already_migrated[resource_id] = new_id

            return {
                "@id": new_id,
                "@type": d["@type"],
                "_rev": 1,
            }

        if isinstance(d, list):
            for i, entry in enumerate(d):
                d[i] = recursively_clone(entry)
            return d

        if isinstance(d, dict):
            for key, entry in d.items():
                d[key] = recursively_clone(entry)
            return d

        raise TypeError("Unknown {d} with type {type(d)}")

    return recursively_clone(deepcopy(dataset))


def _clone_resource(forge_from, forge_to, resource_id, recurse=True):
    r_old = forge_from.retrieve(resource_id, cross_bucket=True)

    r_json = forge_from.as_json(r_old)
    del r_json["id"]

    if recurse:
        for name, data in r_json.items():
            if "id" in data:
                data["id"] = _clone_resource(forge_from, forge_to, data["id"], recurse=False)

    r_new = Resource.from_json(r_json)

    if hasattr(r_old, "distribution"):
        distribution = r_old.distribution
        if isinstance(distribution, Resource):
            r_new.distribution = attach_existing_distribution(forge_to, distribution)
        else:
            r_new.distribution = [attach_existing_distribution(forge_to, d) for d in distribution]

    forge_to.register(r_new)
    return r_new.id


def attach_existing_distribution(forge_to, distribution):
    return forge_to.attach(
        path=distribution.atLocation.location[7:], content_type=distribution.encodingFormat
    )
