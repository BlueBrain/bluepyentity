import click

import entity_manager

@click.command()
@click.argument('id_')
@click.pass_context
def download(ctx, id_):
    """Download ID_ from NEXUS"""
    user = ctx.meta['user']
    env = ctx.meta['env']

    token = entity_manager.token.get_token(env=env, username=user)

    entity_manager.download.download(token, id_, autopath=True)
