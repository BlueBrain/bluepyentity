# SPDX-License-Identifier: LGPL-3.0-or-later

"""token CLI entry point"""
from datetime import datetime

import click
from rich import pretty

import bluepyentity.token


@click.group()
def app():
    """Token Mangement"""


@app.command()
@click.pass_context
def get(ctx):
    """get the currently saved token, print it without formatting"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    tok = bluepyentity.token.get_token(env=env, username=user)
    click.echo(tok)


@app.command(name="set")
@click.pass_context
@click.option("--token", "tok", default=None, help="Value of token to set")
def _set(ctx, tok):
    """set the token, so it can be saved"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bluepyentity.token.set_token(env=env, username=user, token=tok)


@app.command()
@click.pass_context
def decode(ctx):
    """decode the currently saved token, print its expiry"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    tok = bluepyentity.token.get_token(env=env, username=user)
    info = bluepyentity.token.decode(tok)
    pretty.pprint(info)
    expiry = datetime.fromtimestamp(info["exp"])
    pretty.pprint(f"Token expires at {expiry} ({expiry - datetime.now()} from now)")
