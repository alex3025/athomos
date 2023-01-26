from discord.ext import commands
from pymongo import MongoClient

from utils.config import Config


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()

        self.cluster = MongoClient(self.config.db_uri)
        self.db = self.cluster[self.config.db_name]['stats']
    

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.db.insert_one({
            'authorID': ctx.author.id,
            'authorName': str(ctx.author),
            'command': ctx.interaction.command.qualified_name,
            'timestamp': ctx.message.created_at,
            'guild': {
                'id': ctx.guild.id,
                'name': ctx.guild.name,
                'members': ctx.guild.member_count,
            }
        })


async def setup(bot):
    await bot.add_cog(Stats(bot))
