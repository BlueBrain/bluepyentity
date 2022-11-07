# SPDX-License-Identifier: LGPL-3.0-or-later

"""useful utilities"""
from collections import OrderedDict


def visit_container(container, func, dict_func=None):
    """recursively visit a container

    Applies `func` to each non-container element
    if `dict_func` is specified, dictionaries are processed using it and
    return None drops a particular key
    """

    def visit(c):
        if isinstance(c, tuple):
            return tuple(visit(val) for val in c)
        elif isinstance(c, list):
            return [visit(val) for val in c]
        elif isinstance(c, (dict, OrderedDict)):
            if dict_func is None:
                return {k: visit(v) for k, v in c.items()}
            ret = {}
            for k, v in c.items():
                k, v = dict_func(k, v, visit)
                if k is not None:
                    ret[k] = v
            return ret
        elif isinstance(c, set):
            return {visit(v) for v in c}
        return func(c)

    return visit(container)


def ordered2dict(data):
    """convert all `OrderedDict` in data to normal `dict`

    helper to work around the nexus_python_sdk==0.3.2
    """
    return visit_container(data, lambda x: x)
