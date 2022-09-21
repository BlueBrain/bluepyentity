from kgforge.core import KnowledgeGraphForge
from entity_management import environments

import logging

L = logging.getLogger(__name__)

def download(token, id_, autopath=False):
    with environments.get_environment('prod') as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket="bbp/atlas",
            #endpoint='https://staging.nise.bbp.epfl.ch/nexus/v1'
            )
        #searchendpoints={"sparql": {"endpoint": "https://bbp.epfl.ch/neurosciencegraph/data/views/aggreg-sp/dataset"}},

    resource = forge.retrieve(id_, cross_bucket=True)

    if len(resource.distribution) == 0:
        L.error('%s: Resource has nothing to download', id_)
        return
    elif len(resource.distribution) > 1:
        formats = [d.encodingFormat for d in resource.distribution]
        L.error('%s: Resource has multiple distributions: %s', id_, formats)
        return

    forge.download(resource.distribution, "contentUrl", ".", overwrite=True)
