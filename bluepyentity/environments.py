import importlib.resources

import yaml
from kgforge.core import KnowledgeGraphForge

ENVIRONMENTS = {
    "prod": "prod-forge-nexus.yaml",
    "staging": "staging-forge-nexus.yaml",
}


def get_environment(env):
    return importlib.resources.path("bluepyentity.data", ENVIRONMENTS[env])


def create_forge(environment, token, bucket):
    with get_environment(environment) as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket=bucket,
        )
        return forge


def create_nexus_client(environment, token):
    with get_environment(environment) as env:
        with open(env) as fd:
            config = yaml.safe_load(fd)
        endpoint = config["Store"]["endpoint"]

    import nexussdk

    try:
        import nexussdk.config
    except:
        return nexussdk.client.NexusClient(environment=endpoint, token=token)
    else:
        nexussdk.config.set_environment(endpoint)
        nexussdk.config.set_token(token)

        from nexussdk import (
            acls,
            files,
            identities,
            organizations,
            permissions,
            projects,
            realms,
            resolvers,
            resources,
            schemas,
            storages,
            utils,
            views,
        )

        class Client:
            pass

        setattr(Client, "acls", acls)
        setattr(Client, "files", files)
        setattr(Client, "identities", identities)
        setattr(Client, "organizations", organizations)
        setattr(Client, "permissions", permissions)
        setattr(Client, "projects", projects)
        setattr(Client, "realms", realms)
        setattr(Client, "resolvers", resolvers)
        setattr(Client, "resources", resources)
        setattr(Client, "schemas", schemas)
        setattr(Client, "storages", storages)
        setattr(Client, "views", views)
        setattr(Client, "_http", utils.http)

        return Client()
