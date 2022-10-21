import click

import bluepyentity

REQUIRED_PATH = click.Path(exists=True, readable=True, dir_okay=False, resolve_path=True)


# TODO: enable project as an argument ('nse/test2' used for testing)
@click.command()
@click.argument("resource", required=REQUIRED_PATH)
# @click.option("--project, -p", type=str, default="nse/test2", help="target ORGANIZATION/PROJECT")
@click.pass_context
# def register(ctx, resource, project):
def register(ctx, resource):
    """Register a RESOURCE to NEXUS. Supported file formats: .yml/.yaml, .json"""
    user = ctx.meta['user']
    env = ctx.meta['env']

    token = bluepyentity.token.get_token(env=env, username=user)

    bluepyentity.register.register(token, resource)
