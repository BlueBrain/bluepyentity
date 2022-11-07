# SPDX-License-Identifier: LGPL-3.0-or-later

"""info CLI entry point"""

import click
from rich import console, pretty, rule

import bluepyentity
from bluepyentity import utils


@click.group()
def app():
    """Project Management"""


@app.command()
@click.argument("project")
@click.pass_context
def resolvers(ctx, project):
    """print resolvers associated with a project"""
    cons = console.Console()
    user = ctx.meta["user"]
    env = ctx.meta["env"]

    org, project = project.split("/")

    token = bluepyentity.token.get_token(env=env, username=user)
    client = bluepyentity.environments.create_nexus_client(env, token)
    data = utils.ordered2dict(client.resolvers.list(org, project))
    pretty.pprint(data, console=cons)

    for r in data["_results"]:
        resolver = client.resources.fetch(org, project, resource_id=r["@id"])
        resolver = utils.ordered2dict(resolver)
        cons.print(rule.Rule())
        pretty.pprint(resolver, console=cons)
