import logging
import time
import os
import colorlog

from .config import Config


config = Config()

log = logging.getLogger()
log.setLevel(config.logging_level.upper())

# Color Handler
chandler = logging.StreamHandler()

if config.colored_logging:
    chandler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)s%(reset)s: %(white)s%(message)s', datefmt=time.strftime("%d/%m/%Y-%H:%M:%S"), reset=True, log_colors={
        'DEBUG': 'purple',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'white,bg_red'
    }))
else:
    chandler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

log.addHandler(chandler)

# File Handler
if config.save_logs:
    if not os.path.isdir('logs'):
        log.info('Creating "logs" path.')
        os.makedirs('logs')

    fhandler = logging.FileHandler(filename='logs/{}.log'.format(time.strftime("%d-%m-%Y_%H.%M.%S") if not config.purge_logs else 'latest'), encoding='utf-8', mode='w')
    fhandler.setLevel('DEBUG')
    fhandler.setFormatter(logging.Formatter('(%(asctime)s) %(levelname)s: %(message)s', datefmt=time.strftime("%d/%m/%Y-%H:%M:%S")))
    log.addHandler(fhandler)

# Purge logs
if config.purge_logs:
    log.debug('Purging logs...')
    for to_purge in os.listdir('logs'):
        try:
            os.remove("logs/" + to_purge)
        except PermissionError:
            pass


class Logger:
    def __init__(self):
        self.log = log

    def print_traceback(self):
        return config.print_traceback

    def info(self, msg, **kwargs):
        self.log.info(msg, **kwargs)

    def warning(self, msg, **kwargs):
        self.log.warning(msg, **kwargs)

    def error(self, msg, **kwargs):
        self.log.error(msg, **kwargs)

    def debug(self, msg, **kwargs):
        self.log.debug(msg, **kwargs)

    def exception(self, msg, **kwargs):
        self.log.exception(msg, **kwargs)

    def critical(self, msg, **kwargs):
        self.log.critical(msg, **kwargs)
