"""download files or create lines based on entities in the knowledge graph"""
import logging
from pathlib import Path

import bluepyentity.environments

L = logging.getLogger(__name__)


def download(token, id_, bucket, target_path=None, create_link_if_possible=False):
    """download files or create lines based on entities in the knowledge graph"""
    assert target_path is None, "target_path is unsupported, please contribute"
    assert not create_link_if_possible, "create_link_if_possible is unsupported, please contribute"

    forge = bluepyentity.environments.create_forge("prod", token, bucket=bucket)
    resource = forge.retrieve(id_, cross_bucket=True)

    if isinstance(resource.distribution, list):
        if len(resource.distribution) == 0:
            L.error("%s: Resource has nothing to download", id_)
            return
        elif len(resource.distribution) > 1:
            formats = [d.encodingFormat for d in resource.distribution]
            L.error("%s: Resource has multiple distributions: %s", id_, formats)
            return

    if resource.distribution.atLocation.location.startswith("file://"):
        path = Path(resource.distribution.atLocation.location[7:])
        if path.exists():
            (Path() / path.name).symlink_to(path)
            return

    # XXX: should return the path to the file that has been downloaded
    forge.download(resource.distribution, "contentUrl", ".", overwrite=True)
