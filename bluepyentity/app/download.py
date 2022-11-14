# SPDX-License-Identifier: LGPL-3.0-or-later

"""download cli entry point"""

import click
from rich import console, pretty

import bluepyentity
import bluepyentity.environments


@click.command()
@click.argument("id_")
@click.option(
    "--output",
    default=".",
    help="Output directory",
)
@click.option(
    "--create-links-if-possible",
    is_flag=True,
    required=False,
    default=False,
    help="Try creating symbolic links if the storage type allows it.",
)
@click.pass_context
def download(ctx, id_, output, create_links_if_possible):
    """Download `id` from NEXUS"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    token = bluepyentity.token.get_token(env=env, username=user)

    forge = bluepyentity.environments.create_forge(env, token, bucket=bucket)

    ret = bluepyentity.download.download(
        forge, id_, output_dir=output, create_links_if_possible=create_links_if_possible
    )

    cons = console.Console()
    pretty.pprint(ret, console=cons)
