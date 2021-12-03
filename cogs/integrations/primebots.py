import json
import aiohttp
from discord.ext import commands

from utils.config import Config
from utils.logger import Logger


class PrimeBots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.log = Logger()

        self.baseUrl = 'https://primebots.it/api'

        if not self.config.primebots_token:
            try:
                self.bot.unload_extension('cogs.integrations.primebots')
                self.log.info('PrimeBots token not set! Disabling extension.')
            except commands.ExtensionNotLoaded as ex:
                self.log.error(f'The extension "{ex.name}" tried to disable itself but it wasn\'t loaded!')
            finally:    
                return


    # Methods
    async def updateServerCount(self):
        self.log.debug('<PrimeBots> Attempting to post server count...')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.baseUrl}/{self.bot.user.id}/guilds/{self.config.primebots_token}', data=json.dumps({'botGuilds': len(self.bot.guilds)}), headers={'Content-Type': 'application/json'}) as resp:
                    if resp.status == 200:
                        print(await resp.text())
                        self.log.info(f'<PrimeBots> Server count posted!')
                    else:
                        raise Exception()
        except:
            self.log.error('<PrimeBots> Failed to post the server count: HTTP Error.')


    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await self.updateServerCount()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.updateServerCount()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.updateServerCount()


def setup(bot):
    bot.add_cog(PrimeBots(bot))
