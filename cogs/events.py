import discord
from discord.ext import commands

from utils.logger import Logger
from utils.database import Database
from utils.messages import Messages


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.log = Logger()
        self.msg = Messages()
        self.db = Database()

    @commands.Cog.listener()
    async def on_message(self, message):
        # if not message.guild and await self.bot.is_owner(message.author):
        #     await message.add_reaction('📣')
        # else:
        #     return
        if not message.guild:
            return

        if message.author == self.bot.user:
            return

        if message.author.bot:
            return
    
    # @commands.Cog.listener()
    # async def on_reaction_add(self, reaction, user):
    #     if str(reaction) == '📣' and await self.bot.is_owner(user):
    #         await reaction.message.add_reaction('📨')
    #         try:
    #             reaction, user = await self.bot.wait_for('reaction_add', timeout=15, check=lambda reaction, user: user == reaction.message.author and str(reaction) == '📨')
    #         except asyncio.TimeoutError:
    #             print('sas')
    #         else:
    #             await reaction.message.channel.send('EPICO!')
    #         finally:
    #             await reaction.message.remove_reaction('📨', self.bot.user)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.db.on_guild_join(guild)
        self.log.debug(f'Joined in a guild: {guild.name} (ID: {guild.id})')

    # @commands.Cog.listener()
    # async def on_guild_remove(self, guild):
    #     self.log.debug(f'Removed from a guild: {guild.name} (ID: {guild.id})')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Join Message
        joinMessage = self.db.db.find_one({'id': member.guild.id})['messages']['join']
        if joinMessage['message'] and not member.bot:
            try:
                if joinMessage['sendInDm']:
                    await member.send(joinMessage['message'].format_map(self.msg.placeholders(member)))
                else:
                    channel = member.guild.get_channel(joinMessage['textChannel'])
                    await channel.send(joinMessage['message'].format_map(self.msg.placeholders(member)))
            except (KeyError, discord.NotFound) as ex:
                if isinstance(ex, discord.NotFound):
                    self.db.db.update_one({'id': member.guild.id}, {'$set': {'messages.join.textChannel': None}})
                pass

        # Welcome roles
        welcomeRoles = self.db.db.find_one({'id': member.guild.id})['welcomeRoles']
        if len(welcomeRoles) > 0:
            for role in [member.guild.get_role(role) for role in welcomeRoles]:
                try:
                    await member.add_roles(role)
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Leave Message
        leaveMessage = self.db.db.find_one({'id': member.guild.id})['messages']['leave']
        if leaveMessage['message'] and not member.bot:
            try:
                channel = member.guild.get_channel(leaveMessage['textChannel'])
                await channel.send(leaveMessage['message'].format_map(self.msg.placeholders(member)))
            except KeyError:
                pass

async def setup(bot):
    await bot.add_cog(Events(bot))
