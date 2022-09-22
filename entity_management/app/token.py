import click
from rich import pretty

import entity_management.token


@click.group()
def app():
    """Token Mangement"""

@app.command()
def get():
    tok = entity_management.token.get_token()
    click.echo(tok)


@app.command()
@click.option('--token', 'tok', default=None, help="Value of token to set")
def set(tok):
    entity_management.token.set_token(token=tok)


@app.command()
def decode():
    tok = entity_management.token.get_token()
    info = entity_management.token.decode(tok)
    pretty.pprint(info)
