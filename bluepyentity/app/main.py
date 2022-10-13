import getpass
import logging
import click

from bluepyentity.app import download, info, token
from bluepyentity.version import VERSION


USER = getpass.getuser()


@click.group(commands={
    'download': download.download,
    'info': info.info,
    'token': token.app,
})
@click.version_option()
@click.option("-v", "--verbose", count=True, help="Multiple increases logging level")
@click.option("--env", type=str, default="prod", help="Name of the enviroment to use")
@click.option("--user", type=str, default=USER, help="User to login as")
@click.pass_context
def main(ctx, verbose, env, user):
    """The CLI object."""
    logging.basicConfig(
        level=(logging.WARNING, logging.INFO, logging.DEBUG)[min(verbose, 2)],
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ctx.meta['user'] = user
    ctx.meta['env'] = env
