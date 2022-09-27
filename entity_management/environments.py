import importlib.resources

from kgforge.core import KnowledgeGraphForge


ENVIRONMENTS = {
    'prod': 'prod-forge-nexus.yaml'
}


def get_environment(env):
    return importlib.resources.path('entity_management.data', ENVIRONMENTS[env])


def create_forge(env, token, bucket):
    with get_environment('prod') as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket=bucket,
            #endpoint='https://staging.nise.bbp.epfl.ch/nexus/v1'
            )
        return forge
