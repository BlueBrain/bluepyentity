import click
from rich import pretty

import click

import entity_management


@click.command()
@click.option('--metadata', type=bool, default=False)
@click.option('--raw-resource', type=bool, default=False)
@click.argument('id_')
def info(id_, metadata, raw_resource):
    """get info on ID_ from NEXUS"""
    from kgforge.core import KnowledgeGraphForge

    token = entity_management.token.get_token()

    with entity_management.environments.get_environment('prod') as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket="bbp/atlas",
            #endpoint='https://staging.nise.bbp.epfl.ch/nexus/v1'
            )
        #searchendpoints={"sparql": {"endpoint": "https://bbp.epfl.ch/neurosciencegraph/data/views/aggreg-sp/dataset"}},

    if not raw_resource:
        # gross monkey-style patch
        from kgforge.core.resource import Resource
        def __rich_repr__(self):
            for k, v in vars(self).items():
                if not k.startswith('_'):
                    yield f'{k}={v}'
        Resource.__rich_repr__ = __rich_repr__

    #XXX version?
    resource = forge.retrieve(id_, cross_bucket=True)
    rtype = type(resource)
    data = vars(resource)

    if not metadata:
        data = {k: v for k, v in data.items() if not k.startswith('_')}

    pretty.pprint(data)
