# SPDX-License-Identifier: LGPL-3.0-or-later

"""register cli entry point"""

import click
from rich import console, pretty

import bluepyentity

REQUIRED_PATH = click.Path(exists=True, readable=True, dir_okay=False, resolve_path=True)


@click.group()
def app():
    """Registration Mangement"""


@app.command()
@click.argument("resource", required=REQUIRED_PATH)
@click.option("--dry-run", is_flag=True, help="Do not register, just show what would be registered")
@click.pass_context
def entity(ctx, resource, dry_run):
    """Register a RESOURCE to NEXUS. Supported file formats: .yml/.yaml, .json"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    cons = console.Console()
    forge = bluepyentity.environments.create_forge(
        env,
        bluepyentity.token.get_token(env=env, username=user),
        bucket=bucket,
        debug=True,
    )

    resource = bluepyentity.utils.parse_dict_from_file(resource)
    resources = (resource,) if isinstance(resource, dict) else resource

    registrations = [
        bluepyentity.register.register(forge, resource, dry_run=dry_run) for resource in resources
    ]
    if dry_run:
        printout = [
            {"DEFINITION": resource, "PARSED_RESOURCE": forge.as_json(registration)}
            for resource, registration in zip(resources, registrations)
        ]
    else:
        printout = [
            (resource, registration.id) for resource, registration in zip(resources, registrations)
        ]

    pretty.pprint(printout, console=cons)


@app.command()
@click.pass_context
def types(_):
    """List known entitye types"""
    cons = console.Console()
    entities = bluepyentity.entity_definitions.get_registerable_classes()
    pretty.pprint(list(entities.keys()), console=cons)
