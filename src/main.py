from api import *
import logging
import PyInquirer

# TODO: multiprocessing downloads


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filemode="w",
    level=logging.INFO,
)


class DiscordArchiverCLI:
    dc_req = None
    selected_guilds = None

    def main(self):
        self.login()
        self.select_guilds()
        self.select_channels()
        self.download_messages()
        self.download_media()

    def login(self):
        questions = [{
            'type': 'input',
            'name': 'username',
            'message': 'enter your discord username'
        }, {
            'type': 'password', 'name': 'password', 'message': 'enter your discord password'
        }, {
            'type': 'input',
            'name': 'base_path',
            'message': 'enter base path for downloaded files (folders will be created for server/channel)'
        }]
        answers = PyInquirer.prompt(questions)
        self.dc_req = DiscordRequester(
            answers['username'], answers['password'], answers['base_path'])

    def select_guilds(self):
        guilds = []
        for guild in self.dc_req.guilds:
            guilds = guilds + [{'name': guild['name'], 'value': guild['id']}]

        questions = [{
            'type': 'checkbox',
            'name': 'selected_guilds',
            'message': 'select the server',
            'choices': guilds
        }]

        answers = PyInquirer.prompt(questions)
        self.selected_guilds = [{'guild_id': guild_id, 'channel_ids': []}
                                for guild_id in answers['selected_guilds']]
        logging.debug(answers)

    def select_channels(self):

        for selected_guild in self.selected_guilds:
            channels = []
            selected_guild = next(
                guild for guild in self.dc_req.guilds if guild['id'] == selected_guild['guild_id'])

            for channel in selected_guild['channels']:
                channels = channels + \
                    [{'name': channel['name'], 'value': channel['id']}]

            questions = [{
                'type': 'checkbox',
                'name': 'selected_channels',
                'message': 'select the channel',
                'choices': channels
            }]

            answers = PyInquirer.prompt(questions)
            index = next((i for i, guild in enumerate(
                self.selected_guilds) if guild['guild_id'] == selected_guild['id']))
            self.selected_guilds[index]['channel_ids'] = answers['selected_channels']

            logging.debug(answers)

    def download_messages(self):
        for guild in self.selected_guilds:
            for channel_id in guild['channel_ids']:
                logging.info(
                    f"Getting messages for channel {channel_id} in guild {guild['guild_id']}")
                self.dc_req.get_messages(channel_id, guild['guild_id'])

    def download_media(self):
        for guild in self.selected_guilds:
            for channel_id in guild['channel_ids']:
                size = self.dc_req.get_download_size(
                    guild['guild_id'], channel_id)
                questions = [
                    {'type': 'confirm', 'name': 'confirm', 'message': f'Estimated size is {size/1000000} MB, continue?'}]
                answers = PyInquirer.prompt(questions)
                if answers['confirm']:
                    print('download')
                    self.dc_req.download_channel(channel_id, guild['guild_id'])
                else:
                    continue


cli = DiscordArchiverCLI()
cli.main()
