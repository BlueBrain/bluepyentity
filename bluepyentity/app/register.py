import click

import bluepyentity

REQUIRED_PATH = click.Path(exists=True, readable=True, dir_okay=False, resolve_path=True)


@click.command()
@click.argument(
    "resource",
    required=REQUIRED_PATH,
)
@click.pass_context
def register(ctx, resource):
    """Register a RESOURCE to NEXUS. Supported file formats: .yml/.yaml, .json"""
    user = ctx.meta['user']
    env = ctx.meta['env']

    token = bluepyentity.token.get_token(env=env, username=user)

    bluepyentity.register.register(token, resource)
