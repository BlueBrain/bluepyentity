import click

import entity_management

@click.command()
@click.argument('id_')
def download(id_):
    """Download ID_ from NEXUS"""
    token = entity_management.token.get_token()

    entity_management.download.download(token, id_, autopath=True)
