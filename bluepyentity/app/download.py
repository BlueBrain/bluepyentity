"""download cli entry point"""
import click

import bluepyentity


@click.command()
@click.argument("id_")
@click.pass_context
def download(ctx, id_):
    """Download `id` from NEXUS"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    token = bluepyentity.token.get_token(env=env, username=user)

    bluepyentity.download.download(token, id_, bucket)
