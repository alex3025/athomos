import json
from configparser import ConfigParser
from colorama import Fore, Style


class Config:
    def __init__(self, config_file='config/settings.ini'):
        self.parser = ConfigParser()

        self.parser.read(config_file, encoding='utf-8')

        # Bot
        self.bot_token = self.parser.get('Bot', 'token')

        # Logging
        self.logging_level = self.parser.get('Logging', 'loggingLevel', fallback='Info')
        self.save_logs = self.parser.getboolean('Logging', 'saveLogs', fallback=True)
        self.purge_logs = self.parser.getboolean('Logging', 'purgeLogs', fallback=False)
        self.show_settings = self.parser.getboolean('Logging', 'showSettings', fallback=False)
        self.colored_logging = self.parser.getboolean('Logging', 'useColoredLogging', fallback=True)
        self.print_traceback = self.parser.getboolean('Logging', 'fullTraceback', fallback=False)

        # MongoDB
        self.db_uri = self.parser.get('MongoDB', 'databaseURI')
        self.db_name = self.parser.get('MongoDB', 'databaseName')
        self.db_collection_name = self.parser.get('MongoDB', 'collectionName')

        # Integrations
        self.topGG_token = self.parser.get('Integrations', 'topGGToken', fallback=None)
        self.primebots_token = self.parser.get('Integrations', 'primeBotsToken', fallback=None)

        # Misc
        self.embeds_color = int(self.parser.get('Misc', 'embedsColor', fallback='14B5EF'), 16)
        # self.announcements_channel = self.parser.getint('Misc', 'announcementsChannel')

        # # Load lavalink_nodes.json
        # with open('config/lavalink_nodes.json') as ln:
        #     self.lavalink_nodes = json.load(ln)


    def short(self, value):
        if len(value) > 30:
            return value[:30] + '...'
        else:
            return value.capitalize()

    def print_config(self):
        if self.colored_logging:
            colors = {'General': Fore.GREEN, 'Logging': Fore.YELLOW}
        else:
            colors = {'General': Style.RESET_ALL, 'Logging': Style.RESET_ALL}

        for section in self.parser.sections():
            print(f'\n[{colors[section] + section + Style.RESET_ALL}]')
            for (key, value) in self.parser.items(section):
                print(' - {0}: {1}'.format(key, self.short(value)))
