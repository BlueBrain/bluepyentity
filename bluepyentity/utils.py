# SPDX-License-Identifier: LGPL-3.0-or-later

"""useful utilities"""
import getpass
import json
import sys
import termios
from collections import OrderedDict
from functools import partial
from pathlib import Path

import pkg_resources
import yaml

DEFAULT_PARAMS_PATH = pkg_resources.resource_filename(__name__, "default_params.yaml")


class NoDatesSafeLoader(yaml.SafeLoader):
    """SafeLoader without timestamp resolution.

    Modified from:
    https://stackoverflow.com/questions/34667108/ignore-dates-and-times-while-parsing-yaml
        """
    yaml_implicit_resolvers = {
        key: list(filter(lambda tag_re: tag_re[0] != "tag:yaml.org,2002:timestamp", mappings))
        for key, mappings in yaml.SafeLoader.yaml_implicit_resolvers.items()}


FILE_PARSERS = {
    ".yml": partial(yaml.load, Loader=NoDatesSafeLoader),
    ".yaml": partial(yaml.load, Loader=NoDatesSafeLoader),
    ".json": json.load,
}


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


def _in_ipython_notebook():
    """see if we are in an ipython notebook"""
    try:
        return "ZMQInteractiveShell" in str(get_ipython())
    except NameError:
        return False


def get_secret(prompt):
    """works around console `features` to be able to get large tokens

    Empirically, linux only returns up to 4095 characters in `canonical` mode,
    and macOS seems to do ~1023.

    see: https://github.com/python/cpython/issues/89674
    """
    if _in_ipython_notebook() or sys.platform not in ("linux", "linux2", "darwin"):
        return getpass.getpass(prompt=prompt)

    # combination of Lib/unix_getpass and
    # https://github.com/python/cpython/issues/89674
    stream = sys.stdin
    fd = stream.fileno()
    old = termios.tcgetattr(fd)
    new = old[:]
    new[3] &= ~termios.ICANON  # 3 == 'lflags'
    tcsetattr_flags = termios.TCSAFLUSH
    if hasattr(termios, "TCSASOFT"):
        tcsetattr_flags |= termios.TCSASOFT

    try:
        termios.tcsetattr(fd, tcsetattr_flags, new)
        passwd = getpass.getpass(prompt=prompt)
    finally:
        termios.tcsetattr(fd, tcsetattr_flags, old)
        stream.flush()  # issue7208

    return passwd


def parse_dict_from_file(path):
    """Parse dictionary from a file.

    Args:
        path (str): Path to the YAML or JSON file.

    Returns:
        dict: file parsed as a dictionary.
    """
    suffix = Path(path).suffix.lower()
    if suffix not in FILE_PARSERS:
        raise RuntimeError(f"unknown file format: {suffix}")

    with open(path, "r", encoding="utf-8") as fd:
        return FILE_PARSERS[suffix](fd)


def get_default_params(type_):
    """Get default parameters for given type.
    Args:
        type_ (str): type of resource

    Returns:
        dict: default parameters as dict
    """
    return parse_dict_from_file(DEFAULT_PARAMS_PATH).get(type_, {})


def traverse_attributes(item, path):
    """Get item attribute based on given attribute path.

    Args:
        item (dict, object): Item to traverse.
        path (Iterable): Attribute path.

    Returns:
        Any,NoneType: Requested attribute, None if doesn't exist.

    Examples:
        >>> A = {'a': {'b': {'c': 'd'}}}
        ... forgiving_getter(dictionary, ['a', 'b', 'c'])  # Returns: 'd'
        ... forgiving_getter(dictionary, ['a', 'b', 'x'])  # Returns: None
    """
    if not path:
        return item

    if hasattr(item, path[0]):
        return traverse_attributes(getattr(item, path[0]), path[1:])

    return None
