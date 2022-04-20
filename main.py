from asyncio import run, sleep
from base64 import b64encode
from json import load, dump
from sys import stderr
from time import time
from traceback import print_exc

from aiohttp import ClientSession
from credentials import secrets


class Status:
    def __init__(self, title, artists, timestamp, state, idle_to_clear=120):
        self.artist = artists[0]
        self.title = title
        self.timestamp = timestamp / 1000
        self.playing = state
        self.now = time()
        self.idle_time = idle_to_clear

    def __str__(self):
        if not self.playing and self.now - self.timestamp > self.idle_time:
            return ''
        emoji = '▶' if self.playing else '⏸'
        return f'Где-то на просторах Spotify: {emoji}{self.artist} - {self.title}'

    @staticmethod
    async def make_vk_request(method, **kwargs):
        async with ClientSession() as client:
            payload = {
                'access_token': secrets['vk_fake_token'],
                'v': '5.124'
            }
            payload.update(kwargs)
            res = await client.post(f'https://api.vk.com/method/{method}', data=payload)
            return await res.json()

    async def update(self, old):
        if str(old) != str(self):
            await self.make_vk_request('status.set', text=str(self))


class Spotify:
    OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
    API_BASE = 'https://api.spotify.com/v1/'

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = self.load_token()

    def _make_token_auth(self):
        auth_header = b64encode((self.client_id + ':' + self.client_secret).encode('ascii'))
        return {'Authorization': 'Basic %s' % auth_header.decode('ascii')}

    async def get_player(self):
        return await self.make_spotify_req(self.API_BASE + 'me/player')

    async def make_spotify_req(self, url):
        token = await self.get_token()
        return await self.make_get(url, headers={'Authorization': f'Bearer {token}'})

    @staticmethod
    async def make_get(url, headers=None):
        async with ClientSession() as client:
            r = await client.get(url, headers=headers)
            if await r.text():
                return await r.json()
            return {}

    @staticmethod
    async def make_post(url, payload, headers=None):
        async with ClientSession() as client:
            async with client.post(url, data=payload, headers=headers) as r:
                return await r.json()

    @staticmethod
    def load_token():
        return load(open('resources/spotify_auth.json', 'r'))

    def dump_token(self):
        dump(self.token, open('resources/spotify_auth.json', 'w+'))

    async def get_token(self):
        if self.token and not self.check_token():
            return self.token['access_token']

        await self.refresh_token()
        return self.token['access_token']

    def check_token(self):
        return self.token['expires_at'] - time() < 60

    async def refresh_token(self):
        headers = self._make_token_auth()
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token']
        }
        r = await self.make_post(self.OAUTH_TOKEN_URL, payload=payload, headers=headers)
        self.token.update(r)
        self.token['expires_at'] = int(time()) + self.token['expires_in']
        self.dump_token()


class Player:
    def __init__(self, idle_refresh=5, playing_refresh=1):
        self.idle_refresh = idle_refresh
        self.playing_refresh = playing_refresh
        self.spotify = Spotify(secrets['spotify_client_id'], secrets['spotify_client_secret'])
        self.status = None

    async def get_state(self):
        state = await self.spotify.get_player()
        if not state:
            return None, None
        playing = state['is_playing']
        timestamp = state['timestamp']
        artists = [artist['name'] for artist in state['item']['artists']]
        title = state['item']['name']
        status = Status(title, artists, timestamp, playing)
        return playing, status

    async def main_loop(self):
        while True:
            try:
                playing, status = await self.get_state()
                if playing is None:
                    await sleep(self.idle_refresh)
                    continue
                await status.update(self.status)
                self.status = status
                await sleep(self.playing_refresh if playing else self.idle_refresh)
            except Exception as e:
                print(f'Exception in mainloop:\n{e}\n\nTraceback:\n\n------------------------------------------------', file=stderr)
                print_exc()
                print('------------------------------------------------\n\n', file=stderr)


player = Player(5, 5)

run(player.main_loop())
