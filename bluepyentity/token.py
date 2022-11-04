import datetime
import getpass
import logging
import os

import keyring
import jwt

import bluepyentity.utils


L = logging.getLogger(__name__)


def _getuser(username=None):
    if username is None:
        username = getpass.getuser()
    return username


def _token_name(env):
    return f'kgforge:{env}'


def set_token(env, username=None, token=None):
    username = _getuser(username)

    if token is None:
        token = bluepyentity.utils.get_secret(prompt='Token: ')

    if not is_valid(token):
        L.error("Setting the token failed. the length was %d", len(token))
        return

    keyring.set_password(_token_name(env), username, token)


def get_token(env, username=None):
    if 'NEXUS_TOKEN' in os.environ:
        if not is_valid(os.environ['NEXUS_TOKEN']):
            L.error('NEXUS_TOKEN in the env is not valid, either set a working one or remove it')
        return os.environ['NEXUS_TOKEN']

    username = _getuser(username)

    token = keyring.get_password(_token_name(env), username)

    if not is_valid(token):
        set_token(env='prod', username=username)

    return token


def decode(token):
    return jwt.decode(token, options={'verify_signature': False})


def is_valid(token):
    if not token:
        return False

    try:
        info = decode(token)
    except jwt.DecodeError:
        return False

    return ('exp' in info and
            datetime.datetime.now() < datetime.datetime.fromtimestamp(info['exp'])
            )
