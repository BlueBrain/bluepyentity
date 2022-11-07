"""Wrap different environments with different parameters ex: endpoints"""
import importlib.resources

import yaml
from kgforge.core import KnowledgeGraphForge

ENVIRONMENTS = {
    "prod": "prod-forge-nexus.yaml",
    "staging": "staging-forge-nexus.yaml",
}


def get_environment(env):
    """get yaml associated with environment `env`"""
    return importlib.resources.path("bluepyentity.data", ENVIRONMENTS[env])


def create_forge(environment, token, bucket):
    """create a kgforge.KnowledgeGraphForge object"""
    with get_environment(environment) as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket=bucket,
        )
        return forge


def create_nexus_client(environment, token):
    """create a nexus_python_sdk.client object"""
    # pylint: disable=import-outside-toplevel,too-many-locals
    with get_environment(environment) as env:
        with open(env, encoding="utf-8") as fd:
            config = yaml.safe_load(fd)
        endpoint = config["Store"]["endpoint"]

    import nexussdk

    try:
        import nexussdk.config
    except ModuleNotFoundError:
        # pylint: disable=no-member
        return nexussdk.client.NexusClient(environment=endpoint, token=token)
    else:
        nexussdk.config.set_environment(endpoint)
        nexussdk.config.set_token(token)

        from nexussdk import acls as _acls
        from nexussdk import files as _files
        from nexussdk import identities as _identities
        from nexussdk import organizations as _organizations
        from nexussdk import permissions as _permissions
        from nexussdk import projects as _projects
        from nexussdk import realms as _realms
        from nexussdk import resolvers as _resolvers
        from nexussdk import resources as _resources
        from nexussdk import schemas as _schemas
        from nexussdk import storages as _storages
        from nexussdk import utils as _utils
        from nexussdk import views as _views

        class Client:
            """nexus_sdk Client mock"""

            acls = _acls
            files = _files
            identities = _identities
            organizations = _organizations
            permissions = _permissions
            projects = _projects
            realms = _realms
            resolvers = _resolvers
            resources = _resources
            schemas = _schemas
            storages = _storages
            views = _views
            _http = _utils.http

        return Client()
