# SPDX-License-Identifier: LGPL-3.0-or-later

"""token handling"""
import datetime
import functools
import getpass
import logging
import os

import jwt
import keyring

import bluepyentity.utils

L = logging.getLogger(__name__)


def _getuser(username=None):
    if username is None:
        username = getpass.getuser()
    return username


def _token_name(env):
    return f"kgforge:{env}"


def _get_token_bbp_workflow_cli():
    # pylint: disable=import-outside-toplevel, import-error
    try:
        from bbp_workflow_cli.k8s_util import WFL_NS, core_api, get_pod_name
    except ImportError:
        return None

    from kubernetes.stream import stream

    token = stream(
        core_api().connect_get_namespaced_pod_exec,
        get_pod_name(),
        WFL_NS,
        command=["curl", "-s", "-f", "localhost:8000/params/?access_token"],
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    return token


def _get_token_kerberos():
    # pylint: disable=import-outside-toplevel, import-error
    try:
        from requests_kerberos import OPTIONAL, HTTPKerberosAuth
    except ImportError:
        return None

    import random
    from urllib.parse import parse_qs, urlencode, urlsplit

    import requests

    payload = urlencode(
        {
            "client_id": "bbp-nise-nexus-fusion",
            "redirect_uri": "https://bbp.epfl.ch/nexus/web/",
            "response_type": "id_token token",
            "scope": "openid",
            "nonce": str(random.randint(0, int(1e100))),
        }
    )

    url = "https://bbpauth.epfl.ch/auth/realms/BBP/protocol/openid-connect/auth?" + payload

    kerberos_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
    try:
        r = requests.get(url, auth=kerberos_auth, timeout=1.0)
        r.raise_for_status()

        params = parse_qs(urlsplit(r.url).fragment)
        return params["access_token"][0]
    except Exception:  # pylint: disable=broad-except
        return None


def set_token(env, username=None, token=None):
    """set the token for the username and environment

    if `token` is none, it is asked for interactively
    """
    username = _getuser(username)

    for func in (
        _get_token_kerberos,
        _get_token_bbp_workflow_cli,
        functools.partial(bluepyentity.utils.get_secret, prompt="Token: "),
    ):
        if is_valid(token):
            break

        token = func()

    if not is_valid(token):
        L.error("The token could not be decoded or has expired. the length was %d", len(token))
        return

    keyring.set_password(_token_name(env), username, token)


def get_token(env, username=None):
    """try and get the token

    * First from the NEXUS_TOKEN environment variable
    * then from the `keyring`
    * finally, interactively
    """
    if "NEXUS_TOKEN" in os.environ:
        if not is_valid(os.environ["NEXUS_TOKEN"]):
            L.error("NEXUS_TOKEN in the env is not valid, either set a working one or remove it")
        return os.environ["NEXUS_TOKEN"]

    username = _getuser(username)

    token = keyring.get_password(_token_name(env), username)

    if not is_valid(token):
        set_token(env=env, username=username)

    return token


def decode(token):
    """decode the token, and return its contents"""
    return jwt.decode(token, options={"verify_signature": False})


def is_valid(token):
    """check if token is valid

    * if it decodes properly
    * if it has expired
    """
    if not token:
        return False

    try:
        info = decode(token)
    except jwt.DecodeError:
        return False

    return "exp" in info and datetime.datetime.now() < datetime.datetime.fromtimestamp(info["exp"])
