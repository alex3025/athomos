import dbl
from discord.ext import commands

from utils.logger import Logger
from utils.config import Config


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.log = Logger()

        if not self.config.dbl_token:
            try:
                self.bot.unload_extension('cogs.integrations.topgg')
                self.log.info('TopGG token not set! Disabling extension.')
            except commands.ExtensionNotLoaded as ex:
                self.log.error(f'The extension "{ex.name}" tried to disable itself but it wasn\'t loaded!')
            finally:    
                return

        self.dblpy = dbl.DBLClient(self.bot, self.config.dbl_token)


    # Methods
    async def post_server_count(self):
        self.log.debug('<DBL> Attempting to post server count...')
        try:
            await self.dblpy.post_guild_count()
            self.log.info(f'<DBL> Server count posted!')
        except dbl.errors.Forbidden:
            self.log.error('<DBL> Failed to post the server count: No permissions.')
    

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await self.post_server_count()


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.post_server_count()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.post_server_count()


def setup(bot):
    bot.add_cog(TopGG(bot))
