# SPDX-License-Identifier: Apache-2.0
"""Wrap different environments with different parameters ex: endpoints"""

import importlib.resources

import yaml
from kgforge.core import KnowledgeGraphForge

from bluepyentity.exceptions import BluepyEntityError

ENVIRONMENTS = {
    "prod": "prod-forge-nexus.yaml",
    "staging": "staging-forge-nexus.yaml",
}


def get_environment(env):
    """get yaml associated with environment `env`"""
    return importlib.resources.as_file(
        importlib.resources.files("bluepyentity.data").joinpath(ENVIRONMENTS[env])
    )


def create_forge(environment, token, bucket, store_overrides=None, debug=False):
    """Create a kgforge.KnowledgeGraphForge object

    Args:

        environment (str): Name of the configuration environment. Example: 'prod'

        token (str): Nexus access token.

        bucket (str):
            Bucket created by the concatenation of organization and project name.
            Examples: bbp/atlas, bbp/mmb-point-neuron-framework
        store_overrides (dict):
            Optional dictionary with overrides for the Store configuration.

            Allowed store_overrides:
                name: A class name of a store
                endpoint: A URL. Example: https://bbp.epfl.ch/nexus/v1
                searchendpoints:
                 <querytype>: A query paradigm supported by configured store (e.g. sparql)
                   endpoint: An IRI of a query endpoint.
                params:
                   <Store method>: <e.g. register, tag, ...>
                       param: <http query param value to use for the Store method>
                versioned_id_template: A string template using 'x' to access resource fields.
                file_resource_mapping: An Hjson string, a file path, or an URL.
        debug (bool): If True debug mode is enabled.

    Returns:
        A KnowledgeGraphForge instance.

    Raises:
        BluepyEntityError:
            If `store_overrides` keys are different than the specified ones above.

    Examples:
        >>> forge = create_forge('prod', token, 'bbp/atlas')
        >>> forge = create_forge(environment="prod", token=token, bucket="bbp/atlas",
            store_overrides={
                "searchendpoints": {
                    "sparql": {
                        "endpoint": "https://bbp.epfl.ch/neurosciencegraph/data/views/aggreg-sp/dataset"
                    },
                    "elastic": {
                        "endpoint": "https://bbp.epfl.ch/neurosciencegraph/data/views/aggreg-es/dataset",
                        "mapping": "https://bbp.epfl.ch/neurosciencegraph/data/views/es/dataset",
                        "default_str_keyword_field": "keyword",
                    },
                },
            },
            debug=True)
    """
    forge_kwargs = {"debug": debug}
    if store_overrides:
        allowed_keys = {
            "endpoint",
            "searchendpoints",
            "params",
            "versiond_id_template",
            "file_resource_mapping",
        }
        if not all(key in allowed_keys for key in store_overrides):
            raise BluepyEntityError(
                f"Unsupported 'store_overrides' keys. "
                f"Supported: {sorted(allowed_keys)}. "
                f"Encountered: {sorted(store_overrides)}."
            )
        forge_kwargs.update(store_overrides)

    with get_environment(environment) as env:
        forge = KnowledgeGraphForge(
            str(env.absolute()),
            token=token,
            bucket=bucket,
            **forge_kwargs,
        )
        return forge


def get_environment_config(environment):
    """get the config for the `environment`"""
    with get_environment(environment) as env:
        with open(env, encoding="utf-8") as fd:
            return yaml.safe_load(fd)


def create_nexus_client(environment, token):
    """create a nexus_python_sdk.client object"""
    # pylint: disable=import-outside-toplevel,too-many-locals
    config = get_environment_config(environment)
    endpoint = config["Store"]["endpoint"]

    import nexussdk

    try:
        # nexussdk.config was deleted when they moved to having NexusClient,
        # so it's used as canary
        import nexussdk.config
    except ModuleNotFoundError:
        # pylint: disable=no-member
        return nexussdk.client.NexusClient(environment=endpoint, token=token)
    else:
        nexussdk.config.set_environment(endpoint)
        nexussdk.config.set_token(token)

        from urllib.parse import quote_plus as encode_url

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

        def fetch_resource(
            org_label: str,
            project_label: str,
            id_: str,
            resolver_id: str = "_",
            tag: str = None,
            rev: int = None,
        ) -> "Dict":
            """Fetch a resource using resolver.

            Args:
               org_label: Label of the organization the resolver belongs to.
               project_label: Label of the project the resolver belongs to.
               id_: ID of the resolver, given as an IRI which is not URL encoded.
               resolver_id: the resolver ID to use, defaults to '_' which is the 1st resolver
               tag: (optional) Tag of the resolver.
               rev: (optional) Revision number of the resolver.

            Raise an ``Exception`` if ``rev`` and ``tag`` are used together.
            """
            # pylint: disable=protected-access
            _resolvers._check(rev, tag)
            encoded_resolver_id = encode_url(resolver_id)
            encoded_id = encode_url(id_)

            return nexussdk.utils.http.http_get(
                [_resolvers.SEGMENT, org_label, project_label, encoded_resolver_id, encoded_id],
                rev=rev,
                tag=tag,
            )

        _resolvers.fetch_resource = fetch_resource

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
