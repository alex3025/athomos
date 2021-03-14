import asyncio
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

from utils.config import Config
from utils.database import Database
from utils.logger import Logger
from utils.messages import Messages

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Bot(commands.Bot):
    def __init__(self):
        # Set intents to get members amount
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(command_prefix=self.get_custom_prefix, case_insensitive=True, intents=intents)

        self.config = Config()
        self.log = Logger()
        self.msg = Messages()
        self.db = Database().db

        # self.current_lang = lambda message: self.db.get(self.db.Guilds.guild_id == message.guild.id).language

        self.help_links = lambda ctx: [
            (self.msg.get(ctx, 'help.links.invite', 'Invite'), discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(8))),
            (self.msg.get(ctx, 'help.links.support', 'Support'), 'https://discord.gg/6YPEMyj'),
            (self.msg.get(ctx, 'help.links.donate', 'Donate'), 'https://patreon.com/alex3025')
        ]

        self.load_modules()
        self.init()

    async def get_custom_prefix(self, bot, message):
        if not message.guild:
            return
        return commands.when_mentioned_or(self.db.find_one({'id': message.guild.id})['prefix'])(bot, message)

    @tasks.loop(minutes=10.0)
    async def update_stats(self):
        self.log.debug('Updating bot\'s presence...')

        def round_(n):
            return str(n // 1000) + 'k' if n >= 1000 else n

        # Status message
        stats = f'{round_(len(self.guilds))} {"Server" if len(self.guilds) == 1 else "Servers"} | {round_(len(self.users))} {"Utente" if len(self.users) == 1 else "Utenti"}'
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=stats))
        self.log.debug('Presence updated.')

    async def on_ready(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(open('logo.txt', 'r').read() + '\n')

        if self.config.show_settings:
            self.config.print_config()
            print('\n')

        self.log.info('Bot started and connected to Discord!')
        self.log.info(f'Logged with: {self.user.name} (ID: {self.user.id})\n')
        self.update_stats.start()
        # self.db.checkDatabase(self)

    async def on_resumed(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(open('logo.txt', 'r').read() + '\n')
        self.log.info('Bot resumed and connected to discord!')
        self.log.info(f'Logged with: {self.user.name} (ID: {self.user.id})\n')
        self.update_stats.restart()

    def load_modules(self):
        basePath = Path('cogs')
        for file in basePath.rglob("*"):
            directory = file.relative_to(basePath.parent)
            if '__pycache__' not in file.parts and directory.is_file():
                ext = directory.as_posix().replace('/', '.').replace('.py', '')
                try:
                    self.load_extension(ext)
                    self.log.debug(f'Extension "{ext}" loaded!')
                except commands.ExtensionError:
                    self.log.exception(f'Cannot load "{ext}" extension!')
        self.log.info('Extensions loaded!')

    def init(self):
        try:
            if self.config.bot_token:
                self.run(self.config.bot_token, reconnect=True)
            else:
                self.log.critical('Missing token, check the config file! Cannot start the bot.')
        except discord.errors.LoginFailure:
            self.log.critical('Unknow token, check the config file! Cannot start the bot.')
        except:
            self.log.exception('Cannot start the bot!')


Bot()
