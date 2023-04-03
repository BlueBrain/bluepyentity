import click
import bluepyentity
from bluepyentity.app.search.nexus_search import NexusSearch


@click.command()
@click.pass_context
def app(ctx):
    bucket = ctx.meta["bucket"]
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    token = bluepyentity.token.get_token(env=env, username=user)
    app = NexusSearch(css_path="search.scss",
                      bucket=bucket,
                      token=token)
    app.run()