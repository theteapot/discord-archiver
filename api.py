import requests
import shutil
import logging
import cmd
import os
import pathvalidate
import multiprocessing as mp

URL = "https://discord.com"


class DiscordRequester:
    token = ""
    me = None
    guilds = None
    base_path = './'

    def __init__(self, login, password, base_path='./'):
        logging.info("Logging in...")
        resp = requests.post(
            f"{URL}/api/v9/auth/login", json={'login': login, 'password': password}
        )
        logging.debug(resp.json())
        self.base_path = base_path
        self.token = resp.json()['token']
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
        for message in messages:
            if len(message['attachments']) > 0:
                for attachment in message['attachments']:
                    path = os.path.join(output_dir, attachment['id'] + "." +
                                        attachment['filename'].split('.')[-1])
                    if not os.path.exists(path):
                        with requests.get(attachment['url'], stream=True) as r:
                            with open(path, "wb") as f:
                                logging.info(f"Downloading to {path}")
                                shutil.copyfileobj(r.raw, f, 16 * 1024 * 1024)
                    else:
                        logging.debug(f"Path exists {path} skipping")
