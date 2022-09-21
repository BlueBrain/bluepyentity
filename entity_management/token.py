import getpass

import keyring

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

    # TODO: should check if expired here
    if not token:
        set_token(env='prod', username=username, token=token)

    return token
