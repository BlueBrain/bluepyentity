# SPDX-License-Identifier: LGPL-3.0-or-later

"""useful utilities"""
import getpass
import sys
import termios
from collections import OrderedDict
from typing import Optional
from urllib.parse import urlparse

from bluepyentity.exceptions import BluepyEntityError


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


def url_get_revision(url: str) -> Optional[int]:
    """Get the revision number from a url or None otherwise."""
    url = urlparse(url)

    if url.query:
        return int(url.query.replace("rev=", ""))

    return None


def url_with_revision(url: str, revision: int) -> str:
    """Attach a revision to a url.

    Raises:
        BluepyEntityError if the url has already a revision which is different than the input.
    """
    url_revision = url_get_revision(url)

    if url_revision:
        if url_revision == revision:
            return url
        raise BluepyEntityError(
            f"Url '{url}' revision '{url_revision}' does not match the input '{revision}' one."
        )
    return f"{url}?rev={revision}"


def url_without_revision(url: str) -> str:
    """Return the url without the revision query."""
    url = urlparse(url)
    return url._replace(query="").geturl()
