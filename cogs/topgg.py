import dbl
from discord.ext import tasks
from discord.ext import commands

from utils.logger import Logger
from utils.config import Config


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.log = Logger()

        self.dblpy = dbl.DBLClient(self.bot, self.config.dbl_token)
        self.post_server_count.start()

    @tasks.loop(minutes=15.0)
    async def post_server_count(self):
        self.log.debug('Attempting to post server count on DBL...')
        try:
            await self.dblpy.post_guild_count()
            self.log.info(f'Server count posted! ({self.dblpy.guild_count()} Servers)')
        except dbl.errors.Forbidden:
            self.log.error('Failed to post the server count on DBL: No permissions.')


def setup(bot):
    bot.add_cog(TopGG(bot))
