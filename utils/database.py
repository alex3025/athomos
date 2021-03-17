from pymongo import MongoClient

from utils.config import Config
from utils.logger import Logger


log = Logger()
cluster = MongoClient(Config().db_uri)


class Database:
    def __init__(self):
        self.db = cluster[Config().db_name][Config().db_collection_name]


    def on_guild_join(self, guild):
        if self.db.find_one({'id': guild.id}) is None:
            self.db.insert_one({
                'id': guild.id,
                'prefix': '!',
                'language': 'it_IT',
                'messages': {
                    'join': {
                        'message': None,
                        'textChannel': None,
                        'sendInDm': False
                    },
                    'leave': {
                        'message': None,
                        'textChannel': None
                    }
                },
                'welcomeRoles': [],
                'reportsChannel': None,
                'customCommands': {}
            })


    def add_missing_guilds(self, bot):
        addedMissingGuilds = 0

        for guild in bot.guilds:  # Add missing guilds
            if self.db.find_one({'id': guild.id}) is None:  # Not Found
                self.on_guild_join(guild)
                addedMissingGuilds += 1

        if addedMissingGuilds > 0:
            log.info(f'{addedMissingGuilds} missing guild(s) added to the database.')
        
        log.debug('Fixed database guilds references.')
