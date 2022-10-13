import importlib.resources

from kgforge.core import KnowledgeGraphForge


ENVIRONMENTS = {
    'prod': 'prod-forge-nexus.yaml',
    'staging': 'staging-forge-nexus.yaml',
}


def get_environment(env):
    return importlib.resources.path('bluepyentity.data', ENVIRONMENTS[env])


def create_forge(environment, token, bucket):
    with get_environment(environment) as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket=bucket,
            )
        return forge
