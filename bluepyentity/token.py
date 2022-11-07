# SPDX-License-Identifier: LGPL-3.0-or-later

"""token handling"""
import datetime
import getpass
import os

import jwt
import keyring


def _getuser(username=None):
    if username is None:
        username = getpass.getuser()
    return username


def _token_name(env):
    return f"kgforge:{env}"


def set_token(env, username=None, token=None):
    """set the token for the username and environment

    if `token` is none, it is asked for interactively
    """
    username = _getuser(username)

    if token is None:
        token = getpass.getpass()

    keyring.set_password(_token_name(env), username, token)


def get_token(env, username=None):
    """try and get the token

    * First from the NEXUS_TOKEN environment variable
    * then from the `keyring`
    * finally, interactively
    """
    if "NEXUS_TOKEN" in os.environ:
        return os.environ["NEXUS_TOKEN"]

    username = _getuser(username)

    token = keyring.get_password(_token_name(env), username)

    info = decode(token)
    valid = "exp" in info and datetime.datetime.now() < datetime.datetime.fromtimestamp(info["exp"])

    if not token or not valid:
        set_token(env="prod", username=username)

    return token


def decode(token):
    """decode the token, and return its contents"""
    return jwt.decode(token, options={"verify_signature": False})
