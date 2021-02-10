from discord.ext import commands

from utils.logger import Logger
from utils.database import Database
from utils.messages import Messages


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.log = Logger()
        self.db = Database()
        self.msg = Messages()
        self.session = self.db.session

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        elif message.author == self.bot.user:
            return

        if message.author.bot:
            return

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.db.createTables(guild)
        self.log.debug(f'Joined in a guild: {guild.name} (ID: {guild.id})')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.db.deleteTables(guild)
        self.log.debug(f'Removed from a guild: {guild.name} (ID: {guild.id})')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        admin = self.db.get(self.db.Admin.guild_id == member.guild.id, self.db.Admin)

        # Welcome Message
        if admin.join_message and not member.bot:
            try:
                if admin.join_message_sendInDM:
                    await member.send(admin.join_message.format_map(self.msg.placeholders(member)))
                else:
                    channel = member.guild.get_channel(admin.join_message_textChannel)
                    await channel.send(admin.join_message.format_map(self.msg.placeholders(member)))
            except KeyError:
                pass

        # Welcome roles
        if len(admin.welcome_roles) > 0:
            for role in [member.guild.get_role(int(role)) for role in admin.welcome_roles.split(' ')]:
                try:
                    await member.add_roles(role)
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        admin = self.db.get(self.db.Admin.guild_id == member.guild.id, self.db.Admin)

        # Leave Message
        if admin.leave_message and not member.bot:
            try:
                channel = member.guild.get_channel(admin.join_message_textChannel)
                await channel.send(admin.leave_message.format_map(self.msg.placeholders(member)))
            except KeyError:
                pass


def setup(bot):
    bot.add_cog(Events(bot))
