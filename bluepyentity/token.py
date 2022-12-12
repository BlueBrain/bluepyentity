# SPDX-License-Identifier: LGPL-3.0-or-later

"""token handling"""
import datetime
import functools
import getpass
import logging
import os

import jwt
import keyring
from keyring.errors import NoKeyringError

import bluepyentity.utils

L = logging.getLogger(__name__)


def _getuser(username=None):
    if username is None:
        username = getpass.getuser()
    return username


def _token_name(env):
    return f"kgforge:{env}"


def _get_token_environment():
    L.debug("Attempting to get ticket with from the NEXUS_TOKEN enviroment")
    if "NEXUS_TOKEN" in os.environ:
        token = os.environ["NEXUS_TOKEN"]
        if not is_valid(token):
            L.warning("NEXUS_TOKEN in the env is not valid, either set a working one or remove it")
        return token
    return None


def _get_token_kerberos():
    L.debug("Attempting to get ticket with kerberos")
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


def _get_token_keyring(env, username):
    L.debug("Attempting to get ticket from the keyring")
    token = None
    try:
        token = keyring.get_password(_token_name(env), username)
    except NoKeyringError:
        pass

    return token


def set_token(env, username=None, token=None):
    """set the token for the username and environment

    if `token` is invalid, it is asked for interactively
    """
    username = _getuser(username)

    token = bluepyentity.utils.get_secret(prompt="Token: ")

    if not is_valid(token):
        L.error("The token could not be decoded or has expired. the length was %d", len(token))
        return None

    try:
        keyring.set_password(_token_name(env), username, token)
    except NoKeyringError:
        pass

    return token


def get_token(env, username=None):
    """try and get a token, will fall back to interactive if necessary"""
    username = _getuser(username)

    token = None
    for func in (
        functools.partial(_get_token_keyring, env, username),
        _get_token_environment,
        _get_token_kerberos,
    ):
        if is_valid(token):
            break
        token = func()

    if not is_valid(token):
        token = set_token(env=env, username=username)

    return token


def decode(token):
    """decode the token, and return its contents"""
    return jwt.decode(token, options={"verify_signature": False})


def is_valid(token):
    """check if token is valid

    * if it decodes properly
    * if it has not expired
    """
    if not token:
        return False

    try:
        info = decode(token)
    except jwt.DecodeError:
        return False

    return "exp" in info and datetime.datetime.now() < datetime.datetime.fromtimestamp(info["exp"])
