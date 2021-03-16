import discord
import sqlalchemy
from discord.ext import commands
from datetime import datetime

from utils.logger import Logger
from utils.config import Config
from utils.database import Database
from utils.messages import Messages


class Mod(commands.Cog):
    """
    Module containing commands useful for server moderation.
    """

    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.msg = Messages()
        self.db = Database().db
        self.log = Logger()


    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _ban(self, ctx, member: discord.Member, *, reason=None):
        """
        Allows you to ban a member.
        """
        if member == ctx.guild.owner or member == self.bot.user or member == ctx.author:
            await ctx.send(self.msg.get(ctx, 'mod.ban.errors.cannot_ban_this_member', '{error} You cannot ban this member!'))
        else:
            try:
                if reason:
                    await member.send(self.msg.format(self.msg.get(ctx, 'mod.ban.dm.reason', 'You were banned from **{server}** by {author}.\nReason: `{reason}`'), server=ctx.guild.name, author=ctx.author.mention, reason=reason))
                else:
                    await member.send(self.msg.format(self.msg.get(ctx, 'mod.ban.dm.no_reason', 'You were banned from **{server}** by {author}.'), server=ctx.guild.name, author=ctx.author.mention))
            except:
                pass

            await ctx.guild.ban(member, reason=self.msg.format(self.msg.get(ctx, 'mod.ban.audit.reason', 'Banned by {author}.\nReason: {reason}'), author=str(ctx.author), reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.ban.audit.no_reason', 'Banned by {author}.'), author=str(ctx.author)))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.ban.guild.reason', '{success} Banned {banned} from this server.\nReason: `{reason}`'), banned=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.ban.guild.no_reason', '{success} Banned {banned} from this server.'), banned=member.mention))


    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _unban(self, ctx, user: str, *, reason=None):
        """
        Allows you to unban a user.
        """
        bans = await ctx.guild.bans()
        ban_entry = discord.utils.get(bans, user__name=user)
        if ban_entry:
            await ctx.guild.unban(ban_entry.user, reason=self.msg.format(self.msg.get(ctx, 'mod.unban.audit.reason', 'Unbanned by {author}.\nReason: {reason}'), author=str(ctx.author), reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.unban.audit.no_reason', 'Unbanned by {author}.'), author=str(ctx.author)))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.guild.reason', '{success} Unbanned {unbanned} from this server.\nReason: `{reason}`'), unbanned=ban_entry.user.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.guild.no_reason', '{success} Unbanned {unbanned} from this server.'), unbanned=ban_entry.user.mention))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.errors.user_not_found', '{error} Banned user `{user}` not found.'), user=user))


    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def _kick(self, ctx, member: discord.Member, *, reason=None):
        """
        Allows you to kick a member.
        """
        if member == ctx.guild.owner or member == self.bot.user or member == ctx.author:
            await ctx.send(self.msg.get(ctx, 'mod.ban.errors.cannot_kick_this_member', '{error} You cannot kick this member!'))
        else:
            try:
                if reason:
                    await member.send(self.msg.format(self.msg.get(ctx, 'mod.kick.dm.reason', 'You were kicked from **{server}** by {author}.\nReason: `{reason}`'), server=ctx.guild.name, author=ctx.author.mention, reason=reason))
                else:
                    await member.send(self.msg.format(self.msg.get(ctx, 'mod.kick.dm.no_reason', 'You were kicked from **{server}** by {author}.'), server=ctx.guild.name, author=ctx.author.mention))
            except:
                pass

            await ctx.guild.kick(member, reason=self.msg.format(self.msg.get(ctx, 'mod.kick.audit.reason', 'Kicked by {author}.\nReason: {reason}'), author=str(ctx.author), reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.kick.audit.no_reason', 'Kicked by {author}.'), author=str(ctx.author)))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.kick.guild.reason', '{success} Kicked {kicked} from this server.\nReason: `{reason}`'), kicked=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.kick.guild.no_reason', '{success} Kicked {kicked} from this server.'), kicked=member.mention))


    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _mute(self, ctx, member: discord.Member, *, reason=None):
        """
        Allows you to mute a member.
        """
        muted_role = discord.utils.get(ctx.guild.roles, name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
        if not muted_role:
            async with ctx.typing():
                muted_role = await ctx.guild.create_role(name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'), reason=self.msg.get(ctx, 'mod.mute.role.created', 'The muted role didn\'t exist or it was deleted.'))
                for channel in ctx.guild.text_channels:
                    perms = discord.PermissionOverwrite()
                    perms.send_messages = False
                    await channel.set_permissions(muted_role, overwrite=perms)

        if member == ctx.guild.owner or member == self.bot.user or member == ctx.author:
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.cannot_mute_this_member', '{error} You cannot mute this member!'))
        elif muted_role in member.roles:
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.already_muted', '{error} This user is already muted!'))
        else:
            audit_reason = self.msg.format(self.msg.get(ctx, 'mod.mute.audit.reason', 'Muted by {author}.\nReason: {reason}'), author=str(ctx.author), reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.mute.audit.no_reason', 'Muted by {author}.'), author=str(ctx.author))
            try:
                await member.edit(reason=audit_reason)
            except discord.errors.HTTPException:
                pass

            await member.add_roles(muted_role, reason=audit_reason)

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.mute.guild.reason', '{success} Muted {muted} by {author}.\nReason: `{reason}`'), muted=ctx.author.mention, author=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.mute.guild.no_reason', '{success} {muted} was muted by {author}.'), muted=member.mention, author=ctx.author.mention))


    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _unmute(self, ctx, member: discord.Member, *, reason=None):
        """
        Allows you to unmute a member.
        """
        muted_role = discord.utils.get(ctx.guild.roles, name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
        if muted_role in member.roles:
            audit_reason = self.msg.format(self.msg.get(ctx, 'mod.unmute.audit.reason', 'Unmuted by {author}.\nReason: {reason}'), author=str(ctx.author), reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.unmute.audit.no_reason', 'Unmuted by {author}.'), author=str(ctx.author))
            await member.edit(reason=audit_reason)
            await member.remove_roles(muted_role, reason=audit_reason)
            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unmute.guild.reason', '{success} {unmuted} was unmuted.\nReason: `{reason}`'), author=ctx.author.mention, unmuted=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unmute.guild.no_reason', '{success} {unmuted} was unmuted by {author}.'), author=ctx.author.mention, unmuted=member.mention))
        else:
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.not_muted', '{error} This user isn\'t muted!'))


    @commands.command(name='nickname', aliases=['nick'])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def _nickname(self, ctx, member: discord.Member, *, nickname=None):
        """
        Allows you to manage a member's nickname.
        """
        try:
            await member.edit(nick=nickname)
        except discord.errors.Forbidden:
            return await ctx.send(self.msg.get(ctx, 'mod.nickname.errors.cannot_change_nickname', '{error} I can\'t change the nickname of that member.'))

        if nickname:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.nickname.changed', '{success} You changed the nickname of **{user}** to `{nickname}`.'), user=member.name, nickname=nickname))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.nickname.removed', '{success} You removed the nickname of **{user}**.'), user=member.name))


    @commands.command(name='announce', aliases=['broadcast', 'bc'])
    @commands.has_permissions(mention_everyone=True)
    @commands.bot_has_permissions(mention_everyone=True)
    async def _announce(self, ctx, *, message):
        """
        Allows to send a message in all the channels of the server where the bot can write.
        """
        e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'mod.announce.title', ':loudspeaker: Announcement'), description=message, timestamp=datetime.utcnow())
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

        try:
            await ctx.send(embed=e)
        except:
            pass
        finally:
            await ctx.message.add_reaction('<:athomos_success:600278477421281280>')


    @commands.group(name='report', invoke_without_command=True)
    async def _report(self, ctx, member: discord.Member, *, reason):
        """
        Allows you to report a member.

        If you have the necessary permissions, you can set the channel where the reports will be sent.
        """
        channel = self.db.find_one({'id': ctx.guild.id})['reportsChannel']
        if channel:
            e = discord.Embed(colour=int('f44336', 16), title=self.msg.get(ctx, 'mod.report.title', ':warning: Report'), timestamp=datetime.utcnow())
            e.add_field(name=self.msg.get(ctx, 'mod.report.reported', 'User reported:'), value=member.mention, inline=True)
            e.add_field(name=self.msg.get(ctx, 'mod.report.channel', 'Channel:'), value=ctx.channel.mention, inline=True)
            e.add_field(name=self.msg.get(ctx, 'mod.report.reason', 'Reason:'), value=reason, inline=False)
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

            try:
                await self.bot.get_channel(channel).send(embed=e)
            except discord.HTTPException:
                return await ctx.send(self.msg.get(ctx, 'mod.report.errors.reason_too_long', '{error} **Reasong too long!** Maximum 1024 characters allowed.'))

            await ctx.send(self.msg.get(ctx, 'mod.report.report_sent', '{success} **Report sent!** An administrator has been notified.'))
        else:
            if ctx.author.guild_permissions.manage_guild:
                await ctx.send(self.msg.get(ctx, 'mod.report.errors.channel_not_set.full', '{error} **Reports channel not set!** You can set it with: `{prefix}report set <channel>`.'))
            else:
                await ctx.send(self.msg.get(ctx, 'mod.report.errors.channel_not_set.simple', '{error} **Reports channel not set!** Contact an administrator to configure it.'))


    @_report.command(name='set')
    @commands.has_permissions(manage_guild=True)
    async def _report_set(self, ctx, channel: discord.TextChannel=None):
        """
        Allows you to set the channel where the reports will be sent.
        """
        reportsChannel = self.db.find_one({'id': ctx.guild.id})['reportsChannel']

        if channel:
            channel = channel.id
        else:
            channel = ctx.channel.id
        self.db.update_one({'id': ctx.guild.id}, {'$set': {'reportsChannel': channel}})

        channel = self.bot.get_channel(channel).mention
        if reportsChannel:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.report.set.changed', '{success} **Reports channel changed!** All new reports will be sent to {channel}.'), channel=channel))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.report.set.new', '{success} **Reports channel configured!** All new reports will be sent to {channel}.'), channel=channel))


    @_report.command(name='disable', aliases=['unset'])
    @commands.has_permissions(manage_guild=True)
    async def _report_disable(self, ctx):
        """
        Allows you to disable the channel dedicated to reports.
        """
        reportsChannel = self.db.find_one({'id': ctx.guild.id})['reportsChannel']
        if reportsChannel:
            self.db.update_one({'id': ctx.guild.id}, {'$set': {'reportsChannel': None}})
            await ctx.send(self.msg.get(ctx, 'mod.report.remove.disabled', '{success} Reports channel disabled.'))
        else:
            await ctx.send(self.msg.get(ctx, 'mod.report.errors.channel_not_set.full', '{error} **Reports channel not set!** You can set it with: `{prefix}report set <channel>`.'))


    @commands.command(name='ping', aliases=['latency'])
    async def _ping(self, ctx):
        """
        It allows you to control the latency (ping) of the bot.
        """
        ping = round(self.bot.latency * 1000, 2)

        if ping >= 150.0:
            ping_state = '🔴'
        elif ping >= 50.0:
            ping_state = '🟠'
        elif ping <= 50.0:
            ping_state = '🟢'

        await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.ping', '{state} Currently pinging: **{ping}ms**'), state=ping_state, ping=ping))


    async def purge(self, ctx, limit, all_=True):
        if limit > 2000:
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.clean.errors.too_many_messages', '{error} **Too many messages!** Try a lower number. ({limit}/2000)'), limit=limit))

        async with ctx.typing():
            def only_commands(message):
                return message.author == self.bot.user

            deleted = await ctx.channel.purge(limit=limit, check=only_commands if not all_ else lambda m: True)

            try:
                await ctx.message.delete()
            except:
                pass

        await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.clean.cleaned', '{success} Removed **{deleted}** messages.'), deleted=len(deleted)), delete_after=10)

    @commands.group(name='clean', aliases=['clear'], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _clean(self, ctx, limit: int=25):
        """
        Allows you to delete a certain number of messages.

        Default is 25.
        """
        if ctx.invoked_subcommand is None:
            await self.purge(ctx, limit)

    @_clean.command(name='commands', aliases=['bot', 'command'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _clean_commands(self, ctx, limit: int=25):
        """
        Allows you to delete a certain number of bot messages.

        Default is 25.
        """
        await self.purge(ctx, limit, False)


    # # # # # # # # # #
    # ERROR HANDLERS  #
    # # # # # # # # # #

    @_ban.error
    async def _ban_errors(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(self.msg.get(ctx, 'mod.ban.errors.missing_permissions', '{error} You don\'t have the permissions to ban this member.'))


    @_kick.error
    async def _kick_errors(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(self.msg.get(ctx, 'mod.kick.errors.missing_permissions', '{error} You don\'t have the permissions to kick this member.'))


    @_mute.error
    async def _mute_errors(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.missing_permissions', '{error} You don\'t have the permissions to mute this member.'))


    @_unmute.error
    async def _unmute_errors(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(self.msg.get(ctx, 'mod.unmute.errors.missing_permissions', '{error} You don\'t have the permissions to unmute this member.'))


    @_nickname.error
    async def _nickname_errors(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(self.msg.get(ctx, 'mod.nickname.errors.missing_permissions', '{error} You don\'t have the permissions to change the nickname to this member.'))


def setup(bot):
    bot.add_cog(Mod(bot))
