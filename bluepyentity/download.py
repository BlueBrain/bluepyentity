# SPDX-License-Identifier: LGPL-3.0-or-later

"""download files or create lines based on entities in the knowledge graph"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict

from kgforge.core import Resource
from more_itertools import always_iterable

from bluepyentity.exceptions import BluepyEntityError

L = logging.getLogger(__name__)


def download(
    forge, resource_id: str, output_dir: Path | str = ".", create_links_if_possible: bool = False
) -> Dict[str, Path]:
    """Download files based on entities in the knowledge graph.

    Args:
        forge: KnowledgeGraphForge instance.
        resource_id: The id of the resource to download.
        output_dir: Path to output directory. Default is '.'.
        create_link_if_possible: If True symbolic links will be created instead of copies.

    Returns:
        Dictionary the keys of which are the filenames and the values the file paths.
    """
    output_dir = Path(output_dir).resolve()
    resource = forge.retrieve(resource_id, cross_bucket=True)

    if hasattr(resource, "distribution"):
        return _download_distributions(forge, resource, output_dir, create_links_if_possible)

    raise BluepyEntityError(f"Resource {resource_id} does not have distributions to download.")


def _download_distributions(
    forge, resource, output_dir, create_links_if_possible
) -> Dict[str, Path]:

    paths: Dict[str, Path] = {}

    valid_distributions = (
        distribution
        for distribution in always_iterable(resource.distribution)
        if _is_downloadable(distribution)
    )
    for distribution in valid_distributions:
        # pylint: disable=protected-access
        # temp hack to fix the nonexistent store metadata
        if not hasattr(distribution, "_store_metadata") or not distribution._store_metadata:
            assert resource._store_metadata
            distribution._store_metadata = resource._store_metadata

        target_name = distribution.name

        if target_name in paths:
            raise BluepyEntityError(
                "Multiple distributions found with the same filename and extension."
            )

        target_path = output_dir / target_name

        _download_distribution_file(forge, distribution, target_path, create_links_if_possible)

        paths[target_name] = target_path

    return paths


def _is_downloadable(distribution):
    """Return True if distribution has a 'contentUrl'.

    Note: This is also true in the case of gpfs locations.
    """
    if not isinstance(distribution, Resource):
        L.warning("Distribution %s is not a valid resource. Skipped.", distribution)
        return False

    if distribution.type not in (
        "DataDownload",
        "schema:DataDownload",
    ):
        L.warning("Distribution %s is not a DataDownload. Skipped.", distribution)
        return False

    if not hasattr(distribution, "contentUrl"):
        L.warning("Distribution %s does not have a 'contentUrl'. Skipped.", distribution)
        return False

    return True


def _get_filesystem_location(distribution):
    """Return a filesystem location if it's available and exists, otherwise None."""
    try:
        location = distribution.atLocation.location
    except AttributeError:
        L.debug("Distribution object doesn't have an atLocation.")
        return None

    location = Path(_remove_prefix("file://", location))

    if location.exists():
        L.debug("Distribution atLocation location path %s found.", location)
        return location

    L.debug("Distribution atLocation location path %s does not exist.", location)
    return None


def _download_distribution_file(forge, distribution, target_path, create_links_if_possible):

    filesystem_location = _get_filesystem_location(distribution)

    if filesystem_location:
        L.debug("Distribution with file %s has atLocation.", target_path.name)
        _copy_file(filesystem_location, target_path, create_links_if_possible)
    else:
        L.debug("Distribution with file %s doesn't have atLocation.", target_path.name)
        forge.download(
            distribution, follow="contentUrl", path=target_path.parent, cross_bucket=True
        )


def _remove_prefix(prefix: str, path: str) -> str:
    """Return the path without the prefix."""
    if path.startswith(prefix):
        return path[len(prefix) :]
    return path


def _copy_file(source_path: Path, target_path: Path, create_link: bool = True) -> Path:
    source_path = Path(source_path).resolve()
    target_path = Path(target_path).resolve()

    if not source_path.exists():
        raise BluepyEntityError(f"Source path {source_path} does not exist.")

    if target_path.exists():
        L.info("Target %s already exists and will be replaced.", target_path)
        target_path.unlink()

    if create_link:
        target_path.symlink_to(source_path)
        L.debug("Link %s -> %s", source_path, target_path)
    else:
        shutil.copy(source_path, target_path)
        L.debug("Copy %s -> %s", source_path, target_path)
