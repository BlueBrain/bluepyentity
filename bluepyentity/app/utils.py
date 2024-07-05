# SPDX-License-Identifier: Apache-2.0
"""cli/app related utils"""
import bluepyentity.environments
import bluepyentity.utils


def forge_from_ctx(ctx, store_overrides=None):
    """create a nexus-forge object from a click context"""
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    bucket = ctx.meta["bucket"]

    forge = bluepyentity.environments.create_forge(
        env,
        bluepyentity.token.get_token(env=env, username=user),
        bucket=bucket,
        debug=True,
        store_overrides=store_overrides,
    )
    return forge


def rich_resource(resource, strip_under_prefix=True):
    """add __rich_repr__ to a kgforge Resource"""
    data = vars(resource)

    if strip_under_prefix:
        data = {k: v for k, v in data.items() if not k.startswith("_")}

    def _pretty_resource(res):
        if not isinstance(res, type(resource)):
            return res
        bluepyentity.utils.visit_container(vars(res), _pretty_resource)

        def __rich_repr__():
            for k, v in vars(res).items():
                if k.startswith("_"):
                    continue
                yield k, v

        res.__rich_repr__ = __rich_repr__
        return res

    return bluepyentity.utils.visit_container(data, _pretty_resource)
