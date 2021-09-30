import logging
from dotenv import load_dotenv
import os
import api
import pickle

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filemode="w",
    level=logging.DEBUG,
)

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv("PASSWORD")

# Testing multithreading


def test_downloader():
    channel_id = "272180034536734720"
    guild_id = "208822107956707328"
    # api.DiscordRequester(USERNAME, PASSWORD)
    with open('C:\\Users\\Taylor\\code\\discord-archiver\\src\\messages.pkl', 'rb') as file:
        dc_req = pickle.load(file)
    print(dc_req)
    # dc_req.get_messages("886367787067514910", "208822107956707328")
    dc_req.download_channel(channel_id, guild_id)


test_downloader()
