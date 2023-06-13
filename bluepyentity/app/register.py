# SPDX-License-Identifier: LGPL-3.0-or-later

"""register cli entry point"""
import sys
from contextlib import contextmanager

import click
from rich import console, pretty

import bluepyentity

REQUIRED_PATH = click.Path(exists=True, readable=True, dir_okay=False, resolve_path=True)


def _handle_error(error, debug, object_):
    """Print error and exit if debug=False. Raise, otherwise."""
    if debug:
        raise error

    cons = console.Console()

    if object_ is not None:
        pretty.pprint(object_, console=cons)

    message = "\n".join(error.args)
    message = message.replace("[", r"\[")  # escape square brackets (=do not interpret as markup)
    cons.print(f"[red]ERROR: {message}")
    sys.exit(-1)


@contextmanager
def error_handler(debug, object_=None):
    """Handle errors."""
    try:
        yield
    except (bluepyentity.exceptions.BluepyEntityError, NotImplementedError) as error:
        _handle_error(error, debug, object_)


def _parse_definitions(definitions, debug):
    """Parse the definitions."""
    parsed = []
    for definition in definitions:
        with error_handler(debug, definition):
            parsed.append(bluepyentity.register.parse_definition(definition))

    return parsed


def _register_entities(parsed, forge, debug, dry_run, validate):
    """Register parsed entities."""
    regs = []
    for item in parsed:
        with error_handler(debug, item):
            regs.append(
                bluepyentity.register.register(forge, item, dry_run=dry_run, validate=validate)
            )

    return regs


@click.group()
def app():
    """Registration Mangement"""


@app.command()
@click.argument("resource", required=REQUIRED_PATH)
@click.option("--validate", is_flag=True, help="Validate against the schemas in Nexus")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Do not register, just show what would be registered. Implies validate=False",
)
@click.option("--debug", is_flag=True, help="Don't catch errors (=show traceback for all errors)")
@click.pass_context
def entity(ctx, resource, validate, dry_run, debug):
    """Register a RESOURCE to NEXUS. Supported file formats: .yml/.yaml, .json"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    cons = console.Console()
    forge = bluepyentity.environments.create_forge(
        env,
        bluepyentity.token.get_token(env=env, username=user),
        bucket=bucket,
        debug=debug,
    )

    definitions = bluepyentity.utils.parse_file(resource)
    definitions = (definitions,) if isinstance(definitions, dict) else definitions
    parsed = _parse_definitions(definitions, debug)
    registrations = _register_entities(parsed, forge, debug, dry_run, validate)

    if dry_run:
        printout = [
            {"DEFINITION": resource, "PARSED_RESOURCE": forge.as_json(registration)}
            for resource, registration in zip(definitions, registrations)
        ]
    else:
        printout = [
            (resource, registration.id)
            for resource, registration in zip(definitions, registrations)
        ]

    pretty.pprint(printout, console=cons)


@app.command()
@click.pass_context
def types(_):
    """List known entitye types"""
    cons = console.Console()
    entities = bluepyentity.entity_definitions.get_registerable_classes()
    pretty.pprint(list(entities.keys()), console=cons)
