import click
from rich import pretty

import entity_management.token


@click.group()
def app():
    """Token Mangement"""

@app.command()
@click.pass_context
def get(ctx):
    user = ctx.meta['user']
    env = ctx.meta['env']
    tok = entity_management.token.get_token(env=env, username=user)
    click.echo(tok)


@app.command()
@click.pass_context
@click.option('--token', 'tok', default=None, help="Value of token to set")
def set(ctx, tok):
    user = ctx.meta['user']
    env = ctx.meta['env']
    entity_management.token.set_token(env=env, username=user, token=tok)


@app.command()
@click.pass_context
def decode(ctx):
    user = ctx.meta['user']
    env = ctx.meta['env']
    tok = entity_management.token.get_token(env=env, username=user)
    info = entity_management.token.decode(tok)
    pretty.pprint(info)
