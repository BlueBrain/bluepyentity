# SPDX-License-Identifier: LGPL-3.0-or-later

"""register cli entry point"""

import click

import bluepyentity

REQUIRED_PATH = click.Path(exists=True, readable=True, dir_okay=False, resolve_path=True)


@click.command()
@click.argument("resource", required=REQUIRED_PATH)
@click.option("--dry-run", is_flag=True, help="Do not register, just show what would be registered")
@click.pass_context
def register(ctx, resource, dry_run):
    """Register a RESOURCE to NEXUS. Supported file formats: .yml/.yaml, .json"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    forge = bluepyentity.environments.create_forge(
        "prod",
        bluepyentity.token.get_token(env=env, username=user),
        bucket=bucket,
        debug=True,
    )

    bluepyentity.register.register(forge, resource, dry_run=dry_run)
