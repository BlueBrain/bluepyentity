import logging
import os
from pathlib import Path

import bluepyentity
from bluepyentity import environments

L = logging.getLogger(__name__)


def download(token, id_, bucket):
    forge = environments.create_forge("prod", token, bucket=bucket)
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

    forge.download(resource.distribution, "contentUrl", ".", overwrite=True)


# def staging():
