from configparser import ConfigParser
from colorama import Fore, Style


class Config:
    def __init__(self, config_file='config/settings.ini'):
        self.cfg = ConfigParser()

        self.cfg.read(config_file, encoding='utf-8')

        # General
        self.bot_token = self.cfg.get('General', 'token', fallback=None)

        # Logging
        self.logging_level = self.cfg.get('Logging', 'loggingLevel', fallback='Info')
        self.save_logs = self.cfg.getboolean('Logging', 'saveLogs', fallback=True)
        self.purge_logs = self.cfg.getboolean('Logging', 'purgeLogs', fallback=False)
        self.show_settings = self.cfg.getboolean('Logging', 'showSettings', fallback=False)
        self.colored_logging = self.cfg.getboolean('Logging', 'useColoredLogging', fallback=True)
        self.print_traceback = self.cfg.getboolean('Logging', 'fullTraceback', fallback=False)

        # Database
        self.db_uri = self.cfg.get('Database', 'databaseURI', fallback='sqlite:///data.db')

        # Other
        self.embeds_color = int(self.cfg.get('Other', 'embedsColor', fallback='14B5EF'), 16)
        self.dbl_token = self.cfg.get('Other', 'dblToken', fallback=None)

    def value_processor(self, key, value):
        if len(value) > 30:
            return value[:30] + '...'
        else:
            return value.capitalize()

    def print_config(self):
        if self.colored_logging:
            colors = {'General': Fore.GREEN, 'Logging': Fore.YELLOW}
        else:
            colors = {'General': Style.RESET_ALL, 'Logging': Style.RESET_ALL}

        for section in self.cfg.sections():
            print(f'\n[{colors[section] + section + Style.RESET_ALL}]')
            for (key, value) in self.cfg.items(section):
                print(' - {0}: {1}'.format(key, self.value_processor(key, value)))
