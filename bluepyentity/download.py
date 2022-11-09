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

    if distribution.type != "DataDownload":
        L.warning("Distribution %s is not a DataDownload. Skipped.", distribution)
        return False

    if not hasattr(distribution, "contentUrl"):
        L.warning("Distribution %s does not have a 'contentUrl'. Skipped.", distribution)
        return False

    return True


def _has_gpfs_location(distribution):
    try:
        return distribution.atLocation.location.startswith("file:///gpfs")
    except AttributeError:
        return False


def _download_distribution_file(forge, distribution, target_path, create_links_if_possible):

    if _has_gpfs_location(distribution):
        L.debug("Distribution with file %s has atLocation.", target_path.name)
        source_path = Path(_remove_prefix("file://", distribution.atLocation.location))
        _copy_file(source_path, target_path, create_links_if_possible)
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
