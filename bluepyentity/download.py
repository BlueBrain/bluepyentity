from bluepyentity import environments

import logging

L = logging.getLogger(__name__)

def download(token, id_, autopath=False):
    forge = bluepyentity.environments.create_forge('prod', token, bucket="bbp/atlas")
    resource = forge.retrieve(id_, cross_bucket=True)

    if len(resource.distribution) == 0:
        L.error('%s: Resource has nothing to download', id_)
        return
    elif len(resource.distribution) > 1:
        formats = [d.encodingFormat for d in resource.distribution]
        L.error('%s: Resource has multiple distributions: %s', id_, formats)
        return

    forge.download(resource.distribution, "contentUrl", ".", overwrite=True)


#def staging():
