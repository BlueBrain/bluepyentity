import click

import bluepyentity.clone
import bluepyentity.environments
import bluepyentity.token


@click.command()
@click.option("--to")
@click.argument("id_")
@click.pass_context
def app(ctx, id_, to):
    """get info on `id` from NEXUS"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]
    clone(user, env, bucket, id_, to)


def clone(user, env, bucket, id_, to=None):
    token = bluepyentity.token.get_token(env=env, username=user)
    forge_from = bluepyentity.environments.create_forge(env, token, bucket)

    if to is None:
        forge_to = forge_from
    else:
        to_env, to_bucket = to.split(":")
        forge_to = bluepyentity.environments.create_forge(to_env, token, to_bucket)

    resource = forge_from.retrieve(id_, cross_bucket=True)

    assert resource.id

    new_resource = bluepyentity.clone.clone_grouped_dataset_resource(forge_from, forge_to, resource)

    print(
        "Old Resource:\n"
        f"\tid : {resource.id}\n"
        f"\turl: {resource._store_metadata._self}\n"
        "New Resource:\n"
        f"\tid : {new_resource.id}\n"
        f"\turl: {new_resource._store_metadata._self}"
    )
