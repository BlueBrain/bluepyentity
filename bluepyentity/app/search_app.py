# SPDX-License-Identifier: LGPL-3.0-or-later

"""search application entry point"""
import click
import bluepyentity
from bluepyentity.app.search.nexus_search import NexusSearch


@click.command()
@click.pass_context
@click.option("--log", "log_dir", default=None, help="Directory to dump requests log")
def app(ctx, log_dir):
    bucket = ctx.meta["bucket"]
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    token = bluepyentity.token.get_token(env=env, username=user)
    app = NexusSearch(css_path="search.scss",
                      bucket=bucket,
                      token=token,
                      log_dir=log_dir)
    app.run()
