import os
import sys
import asyncio
import discord
from discord.ext import commands
from discord.ext import tasks

from utils.config import Config
from utils.logger import Logger
from utils.messages import Messages
from utils.database import Database


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Athomos(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.prefix, case_insensitive=True)

        self.config = Config()
        self.log = Logger()
        self.msg = Messages()
        self.db = Database()

        self.current_lang = lambda message: self.db.get(self.db.Guild.guild_id == message.guild.id).language

        self.help_links = lambda ctx: [
            (self.msg.get(ctx, 'help.links.invite', 'Invite'), discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(8))),
            (self.msg.get(ctx, 'help.links.support', 'Support'), 'https://discord.gg/6YPEMyj'),
            (self.msg.get(ctx, 'help.links.donate', 'Donate'), 'https://paypal.me/alex3025')
        ]

        self.load_modules()
        self.run_()

    async def prefix(self, bot, message):
        if not message.guild:
            return
        return commands.when_mentioned_or(self.db.get(self.db.Guild.guild_id == message.guild.id).prefix)(bot, message)

    @tasks.loop(minutes=15.0)
    async def update_stats(self):
        self.log.debug('Updating presence...')

        def round_(n):
            return str(n // 1000) + 'k' if n >= 1000 else n

        # Status message
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{round_(len(self.guilds))} {"Server" if len(self.guilds) == 1 else "Servers"} | {round_(len(self.users))} {"Utente" if len(self.users) == 1 else "Utenti"}'))
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

    async def on_resumed(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(open('logo.txt', 'r').read() + '\n')
        self.log.info('Bot resumed and connected to discord!')
        self.log.info(f'Logged with: {self.user.name} (ID: {self.user.id})\n')
        self.update_stats.restart()

    async def on_message(self, message):
        if not message.guild:  # Disable DMs
            return
        elif message.author == self.user:  # Disable Auto-Reply
            return
        else:
            await self.process_commands(message)

    def load_modules(self):
        for cog in os.listdir('cogs'):
            if cog.endswith('.py'):
                ext = cog.replace('.py', '')
                try:
                    self.load_extension('cogs.' + ext)
                    self.log.debug(f'Extension "{ext.title()}" loaded!')
                except:
                    self.log.exception(f'Cannot load "{ext.title()}" extension!')
        self.log.info('Extensions loaded!')

    def run_(self):
        try:
            if self.config.bot_token:
                self.run(self.config.bot_token, reconnect=True)
            else:
                self.log.critical('Missing token, check the config file! Cannot start the bot.')
        except:
            self.log.critical('Unknow token, check the config file! Cannot start the bot.')


Athomos()
