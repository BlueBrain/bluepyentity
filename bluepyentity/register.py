import kgforge

import bluepyentity as em


def _add_defaults(resource):
    """Add default values if not defined.

    Args:
        resource (dict): Resource as dictionary.
    Returns:
        dict: dict with appended defaults

    """
    return dict(resource, **em.utils.get_default_params(resource['type']))


def create_resource(path):
    """Create resource from parameters defined in a file.

    Args:
        path (str): Path to the YAML or JSON file.

    Returns:
        kgforge.core.Resource: Resource instance.
    """
    resource = em.utils.parse_dict_from_file(path)
    resource = _add_defaults(resource)

    return kgforge.core.Resource.from_json(resource)


def register(token, resource_def):
    """Register a Resource in Nexus.

    The parameters of the resource are given in a file.

    Args:
        token (str): NEXUS access token.
        resource_def (str): Path to the YAML or JSON file.
    """
    # TODO:
    # - check if resource in predefined types
    # - check if resource already exists?
    # --- does NEXUS check this?
    # - check if the definition conforms to expected schema/format
    resource = create_resource(resource_def)
    forge = em.environments.create_forge('prod', token, bucket="nse/test2")
    # forge =EM.environments.create_forge('prod', token, bucket="bbp/atlas")
    __import__('pdb').set_trace()
    print()
