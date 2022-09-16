import topgg
from discord.ext import commands

from utils.logger import Logger
from utils.config import Config


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.log = Logger()

        if not self.config.topGG_token:
            try:
                self.bot.unload_extension('cogs.integrations.topgg')
                self.log.info('TopGG token not set! Disabling extension.')
            except commands.ExtensionNotLoaded as ex:
                self.log.error(f'The extension "{ex.name}" tried to disable itself but it wasn\'t loaded!')
            finally:    
                return

        self.topgg = topgg.DBLClient(self.bot, self.config.topGG_token)


    # Methods
    async def postServerCount(self):
        self.log.debug('<TopGG> Attempting to post server count...')
        try:
            await self.topgg.post_guild_count()
            self.log.info(f'<TopGG> Server count posted!')
        except (topgg.errors.Forbidden, topgg.errors.HTTPException):
            self.log.error('<TopGG> Failed to post the server count: No permissions.')
    

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await self.postServerCount()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.postServerCount()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.postServerCount()


async def setup(bot):
    await bot.add_cog(TopGG(bot))
