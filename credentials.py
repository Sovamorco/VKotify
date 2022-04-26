from pathlib import Path

from hvac import Client

_client = Client(url='http://vault:8200')
_creds = Path('/run/secrets/vkotify_vault').read_text().strip().split(':', 1)
_client.auth.userpass.login(
    username=_creds[0],
    password=_creds[1],
)


def get_secret(key):
    read_response = _client.secrets.kv.v2.read_secret_version(path=key)
    data = read_response['data']['data']
    if len(data) == 1 and list(data.keys())[0] == 'value':
        data = data['value']
    return data


_secrets = [
    'spotify_client_secret',
    'spotify_client_id',
    'vk_fake_token',
]

secrets = {}
for item in _secrets:
    secrets[item] = get_secret(item)
