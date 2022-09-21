import importlib.resources


ENVIRONMENTS = {
    'prod': 'prod-forge-nexus.yaml'
}


def get_environment(env):
    return importlib.resources.path('entity_management.data', ENVIRONMENTS[env])
