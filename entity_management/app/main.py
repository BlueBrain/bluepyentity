import logging
import click

from entity_management.app import download, token
from entity_management.version import VERSION

@click.group(commands={
    'download': download.download,
    'token': token.app,
})
@click.version_option()
@click.option("-v", "--verbose", count=True, help="Multiple increases logging level")
#@click.argument("--env", type=str, default="prod", help="Name of the enviroment to use")
#@click.argument("--user", type=str, help="User to login as")
def main(verbose):
    """The CLI object."""
    logging.basicConfig(
        level=(logging.WARNING, logging.INFO, logging.DEBUG)[min(verbose, 2)],
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == '__main__':
    main()
