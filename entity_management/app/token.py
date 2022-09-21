
import click

from entity_management import token

@click.group()
def app():
    """Token Mangement"""

@app.command()
def get():
    tok = token.get_token()
    click.echo(tok)


@app.command()
def set():
    token.set_token()
