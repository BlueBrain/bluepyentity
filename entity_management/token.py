import datetime
import getpass

import keyring
import jwt

def _token_name(env):
    return f'kgforge:{env}'

def set_token(env='prod', username=None, token=None):
    if username is None:
        username = getpass.getuser()

    if token is None:
        token = getpass.getpass('Token: ')
        print(token)

    keyring.set_password(_token_name(env), username, token)


def get_token(env='prod', username=None):
    if username is None:
        username = getpass.getuser()

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
