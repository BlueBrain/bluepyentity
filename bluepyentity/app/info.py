import sys

import click
from rich import pretty, text, console

import click

import bluepyentity
from bluepyentity import utils

def extra_print(cons, store_metadata):
    import dateutil
    from rich.rule import Rule
    from rich.text import Text
    contents = [Rule(),
                ]
    createdAt = dateutil.parser.parse(store_metadata['_createdAt']).replace(microsecond = 0)
    updatedAt = dateutil.parser.parse(store_metadata['_updatedAt']).replace(microsecond = 0)
    contents.extend([
        f"[green]Full ID[/]: {store_metadata['id']}?rev={store_metadata['_rev']}",
        f"[green]Project[/]: {store_metadata['_project']}",
        f"[green]Created / Updated by[/]: {store_metadata['_createdBy']} / {store_metadata['_updatedBy']}",
        f"[green]Created / Updated at[/]: {createdAt} / {updatedAt} -> diff {updatedAt - createdAt}",
        ])

    if store_metadata['id'] != store_metadata['_self']:
        contents.append(
        f"[red]_self != id: [/] {store_metadata['id']} != {store_metadata['_self']}"
        )

    if store_metadata['_deprecated']:
        contents.append("[red] Deprecated")

    contents.append(Rule())

    for c in contents:
        cons.print(c)


@click.command()
@click.option('--metadata', type=bool, default=False)
@click.option('--raw-resource', type=bool, default=False)
@click.argument('id_')
@click.pass_context
def info(ctx, id_, metadata, raw_resource):
    """get info on ID_ from NEXUS"""
    cons = console.Console()

    user = ctx.meta['user']
    env = ctx.meta['env']
    bucket = ctx.meta['bucket']

    token = bluepyentity.token.get_token(env=env, username=user)
    forge = bluepyentity.environments.create_forge(env, token, bucket)

    #XXX version?
    resource = forge.retrieve(id_, cross_bucket=True)
    if resource is None:
        cons.print(f'[red]Unable to find a resource with id: {id_}')
        sys.exit(-1)

    store_metadata = resource._store_metadata
    rtype = type(resource)
    data = vars(resource)

    if not metadata:
        data = {k: v for k, v in data.items() if not k.startswith('_')}

    if not raw_resource:
        def pretty_resource(res):
            if not isinstance(res, rtype):
                return res
            utils.visit_container(vars(res), pretty_resource)

            def __rich_repr__():
               for k, v in vars(res).items():
                   if k.startswith('_'):
                       continue
                   yield k, v

            res.__rich_repr__ = __rich_repr__
            return res

        data = utils.visit_container(data, pretty_resource)

    if 1 or add_rev:
        extra_print(cons, store_metadata)

    pretty.pprint(data, console=cons)
