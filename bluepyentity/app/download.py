"""download cli entry point"""
import click

import bluepyentity
import bluepyentity.environments


@click.command()
@click.argument("id_")
@click.option(
    "--create-links-if-possible",
    is_flag=True,
    required=False,
    default=False,
    help="Try creating symbolic links if the storage type allows it.",
)
@click.pass_context
def download(ctx, id_, create_links_if_possible):
    """Download `id` from NEXUS"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    token = bluepyentity.token.get_token(env=env, username=user)

    forge = bluepyentity.environments.create_forge("prod", token, bucket=bucket)

    bluepyentity.download.download(forge, id_, create_links_if_possible=create_links_if_possible)
