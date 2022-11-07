"""token handling"""
import datetime
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


def set_token(env, username=None, token=None):
    """set the token for the username and environment

    if `token` is none, it is asked for interactively
    """
    username = _getuser(username)

    if token is None:
        token = bluepyentity.utils.get_secret(prompt="Token: ")

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
