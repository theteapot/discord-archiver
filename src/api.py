import requests
import shutil
import logging
import cmd
import os
import pathvalidate
import threading
import time
import pickle
from concurrent.futures import as_completed
from requests_futures.sessions import FuturesSession
from concurrent.futures import ProcessPoolExecutor

# cookies = requests.session()
# cookies.get("https://discord.com")
# print(cookies.cookies)

# cookies = {
#     "__dcfduid": "c842f7a020ee11ec9ec9cdcc9515a788",
#     "__sdcfduid": "c842f7a120ee11ec9ec9cdcc9515a788e0fd41d12d19298a519a9eedbf09aff150a909d74f24f07b9ebc9831848cfdc6",
#     "_gcl_au": "1.1.958868132.1632897048",
#     "locale": "en-US",
#     "OptanonConsent": "isIABGlobal=false&datestamp=Wed+Sep+29+2021+06:30:47+GMT+0000+(Coordinated+Universal+Time)&version=6.17.0&hosts=&landingPath=https://discord.com/&groups=C0001:1,C0002:1,C0003:1"
# }


URL = "https://discord.com"


class DiscordRequester:
    token = ""
    me = None
    guilds = None
    base_path = './'
    session = requests.session()
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0 rv: 91.0) Gecko/20100101 Firefox/91.0'
    }

    def __init__(self, login, password, base_path='./'):
        logging.info("Logging in...")
        # Set initial cookies
        self.session.get("https://discord.com/login")
        print(self.session.cookies)
        resp = self.session.post(
            f"{URL}/api/v9/auth/login", json={'login': login, 'password': password})
        logging.debug(resp.json())
        self.base_path = base_path
        try:
            self.token = resp.json()['token']
        except KeyError as e:
            logging.error(f"Expected token, got {resp.json()}")
        self.me = self.get_me()
        logging.info("Getting servers...")
        self.guilds = self.get_guilds()
        logging.info("Getting channels...")
        for guild in self.guilds:
            guild['channels'] = self.get_guild_channels(guild['id'])

    def get(self, endpoint, headers={}, params={}):
        headers['Authorization'] = self.token
        resp = requests.get(f"{URL}{endpoint}", headers=headers, params=params)
        return resp.json()

    def get_me(self):
        resp = self.get("/api/v9/users/@me")
        logging.debug(resp)
        return resp

    def get_guilds(self):
        resp = self.get('/api/v9/users/@me/guilds')
        logging.debug(resp)
        return resp

    def get_guild_channels(self, guild_id):
        resp = self.get(f'/api/v9/guilds/{guild_id}/channels')
        logging.debug(resp)
        return resp

    def download_channel(self, channel_id, guild_id):
        guild = next(
            guild for guild in self.guilds if guild['id'] == guild_id)

        channel = next(
            channel for channel in guild['channels'] if channel['id'] == channel_id)

        path = pathvalidate.sanitize_filepath(
            os.path.join(self.base_path, guild['name'], channel['name']), platform='auto')
        if not os.path.exists(path):
            os.makedirs(path)

        logging.info(
            f"Downloading channel {channel['name']} from server {guild['name']}")
        self.download_channel_media(channel['messages'], path)

    def get_download_size(self, guild_id, channel_id):
        total_size = 0
        guild = next(guild for guild in self.guilds if guild['id'] == guild_id)
        channel = next(
            channel for channel in guild['channels'] if channel['id'] == channel_id)

        for m in channel['messages']:
            if len(m['attachments']) > 0:
                for a in m['attachments']:
                    total_size = total_size + a['size']
        return total_size

    def get_messages(self, channel_id, guild_id, limit=100, before=None):
        params = {'limit': limit, 'before': before}
        messages = []

        resp = self.get(
            f'/api/v9/channels/{channel_id}/messages', params=params)
        logging.debug(resp)
        messages = messages + resp

        if len(resp) == limit:
            messages = messages + \
                self.get_messages(channel_id, guild_id,
                                  limit, before=resp[-1]['id'])

        g_index = next((i for i, guild in enumerate(
            self.guilds) if guild['id'] == guild_id))
        c_index = next((i for i, channel in enumerate(
            self.guilds[g_index]['channels']) if channel['id'] == channel_id))
        self.guilds[g_index]['channels'][c_index]['messages'] = messages

        return messages

    def download_channel_media(self, messages, output_dir):
        download_targets = []

        # Find all attachments for all messages
        for message in messages:
            if len(message['attachments']) > 0:
                with FuturesSession() as session:
                    for attachment in message['attachments']:
                        path = os.path.join(output_dir, attachment['id'] + "." +
                                            attachment['filename'].split('.')[-1])
                        if not os.path.exists(path):
                            download_targets.append((path,
                                                     attachment['url']))
        # Get all attachments
        with FuturesSession() as session:
            futures = []
            for target in download_targets:
                future = session.get(target[1])
                future.path = target[0]
                futures.append(future)

            for i, future in enumerate(as_completed(futures)):
                resp = future.result()
                with open(future.path, "wb") as f:
                    logging.info(f"Downloading to {path}")
                    f.write(resp.content)
                # Remove responses from memory after usage
                # to conservere memory
                futures[i] = None

    def pickle_self(self):
        logging.debug(f"Picking self...")
        with open('messages.pkl', 'wb') as file:
            pickle.dump(self, file)
        logging.debug(f"Pickle complete")
