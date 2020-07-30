from discord.ext import commands

from utils.logger import Logger
from utils.database import Database


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.db = Database()
        self.log = Logger()
        self.session = self.db.session

        self.placeholders = lambda member: {'JoinedAtDate': member.joined_at.strftime('%d/%m/%Y'), 'JoinedAtTime': member.joined_at.strftime('%H:%M'), 'Mention': member.mention, 'Username': member.name, 'ServerName': member.guild.name, 'ServerMembersCount': len(member.guild.members)}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.author.bot:
            return

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # self.session.add(self.db.Guild(guild_id=guild.id, language=guild.preferred_locale.replace('-', '_') if guild.preferred_locale.replace('-', '_') + '.json' in os.listdir('config/i18n/') else 'en_EN'))
        self.session.add(self.db.Guild(guild_id=guild.id))
        self.session.commit()
        self.log.debug(f'Joined in a guild: {guild.name} (ID: {guild.id})')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.session.delete(self.db.get(self.db.Guild.guild_id == guild.id))
        self.session.commit()
        self.log.debug(f'Removed from a guild: {guild.name} (ID: {guild.id})')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        admin = self.db.get(self.db.Admin.guild_id == member.guild.id, self.db.Admin)

        class format_dict(dict):
            def __missing__(self, key):
                return '{%s}' % key

        # Welcome Message
        if admin.join_message and not member.bot:
            try:
                if admin.join_message_sendInDM:
                    await member.send(admin.join_message.format_map(format_dict(self.placeholders(member))))
                else:
                    channel = member.guild.get_channel(admin.join_message_textChannel)
                    await channel.send(admin.join_message.format_map(format_dict(self.placeholders(member))))
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

        class format_dict(dict):
            def __missing__(self, key):
                return '{%s}' % key

        # Leave Message
        if admin.leave_message and not member.bot:
            try:
                channel = member.guild.get_channel(admin.join_message_textChannel)
                await channel.send(admin.leave_message.format_map(format_dict(self.placeholders(member))))
            except KeyError:
                pass


def setup(bot):
    bot.add_cog(Events(bot))
