import datetime
import getpass
import os

import keyring
import jwt


def _getuser(username=None):
    if username is None:
        username = getpass.getuser()
    return username

def _getpass():
    from rich.prompt import Prompt
    token = Prompt.ask("Token", password=True)
    return token


def _token_name(env):
    return f'kgforge:{env}'


def set_token(env, username=None, token=None):
    username = _getuser(username)

    if token is None:
        token = _getpass()

    keyring.set_password(_token_name(env), username, token)


def get_token(env, username=None):
    if 'NEXUS_TOKEN' in os.environ:
        return os.environ['NEXUS_TOKEN']

    username = _getuser(username)

    token = keyring.get_password(_token_name(env), username)

    info = decode(token)
    valid = ('exp' in info and
             datetime.datetime.now() < datetime.datetime.fromtimestamp(info['exp'])
             )

    if not token or not valid:
        set_token(env='prod', username=username)

    return token


def decode(token):
    return jwt.decode(token, options={'verify_signature': False})
