import os
import tornado.web
from discord.ext import commands

from utils.logger import Logger
from utils.config import Config
from utils.database import Database
from utils.messages import Messages


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, bot, msg, log, db):
        self.bot = bot
        self.msg = msg
        self.log = log
        self.db = db
        self.session = self.db.session

    def get_language(self, fallback='en_EN'):
        lang = self.get_argument('lang', fallback)
        if lang + '.json' not in os.listdir('config/i18n/'):
            lang = fallback
        return lang, None

    async def prepare(self):
        await self.bot.wait_until_ready()


class Commands(BaseHandler):
    async def get(self):
        self.set_status(200)
        commands = {cmd.qualified_name: {'description': self.msg.get(self.get_language(), 'command_descriptions.' + cmd.qualified_name.lower().replace(' ', '.'), ''), 'aliases': cmd.aliases} for cmd in self.bot.walk_commands() if cmd.parent is None}
        self.write(tornado.escape.json_encode(commands))
        self.finish()


class API(commands.Cog):
    def __init__(self, bot):
        self.config = Config()
        self.log = Logger()

        parameters = {
            'bot': bot,
            'msg': Messages(),
            'log': self.log,
            'db': Database()
        }

        endpoints = [
            (r'/commands', Commands, parameters),
        ]

        self.app = tornado.web.Application(endpoints)
        self.app.listen(8000)
        self.log.info('API server started.')


def setup(bot):
    bot.add_cog(API(bot))
