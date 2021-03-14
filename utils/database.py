from pymongo import MongoClient
from utils.config import Config


cluster = MongoClient(Config().db_uri)

class Database:
    def __init__(self):
        self.db = cluster['athomos']['guilds']

    def on_guild_join(self, guild):
        pass

    def on_guild_leave(self, guild):
        pass
