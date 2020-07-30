import discord
import sqlalchemy
from discord.ext import commands
from datetime import datetime

from utils.logger import Logger
from utils.config import Config
from utils.database import Database
from utils.messages import Messages


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.msg = Messages()
        self.db = Database()
        self.log = Logger()
        self.session = self.db.session

        self.mod = lambda guild: self.db.get(self.db.Mod.guild_id == guild.id, self.db.Mod)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.session.add(self.db.Mod(guild_id=guild.id))
        self.session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            self.session.delete(self.mod(guild))
            self.session.commit()
        except sqlalchemy.orm.exc.UnmappedInstanceError:
            pass

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _ban(self, ctx, member: discord.Member, *, reason=None):
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

            await ctx.guild.ban(member, reason=self.msg.format(self.msg.get(ctx, 'mod.ban.audit.reason', 'Banned by {author}.\nReason: {reason}'), author=ctx.author.name, reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.ban.audit.no_reason', 'Banned by {author}.'), author=ctx.author.name))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.ban.guild.reason', '{success} Banned {banned} from this server.\nReason: `{reason}`'), banned=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.ban.guild.no_reason', '{success} Banned {banned} from this server.'), banned=member.mention))

    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _unban(self, ctx, user: str, *, reason=None):
        bans = await ctx.guild.bans()
        ban_entry = discord.utils.get(bans, user__name=user)
        if ban_entry:
            await ctx.guild.unban(ban_entry.user, reason=self.msg.format(self.msg.get(ctx, 'mod.unban.audit.reason', 'Unbanned by {author}.\nReason: {reason}'), author=ctx.author.name, reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.unban.audit.no_reason', 'Unbanned by {author}.'), author=ctx.author.name))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.reason', '{success} Unbanned {banned} from this server.\nReason: `{reason}`'), banned=ban_entry.user.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.no_reason', '{success} Unbanned {banned} from this server.'), banned=ban_entry.user.mention))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unban.errors.user_not_found', '{error} Banned user `{user}` not found.'), user=user))

    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def _kick(self, ctx, member: discord.Member, *, reason=None):
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

            await ctx.guild.kick(member, reason=self.msg.format(self.msg.get(ctx, 'mod.kick.audit.reason', 'Kicked by {author}.\nReason: {reason}'), author=ctx.author.name, reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.kick.audit.no_reason', 'Kicked by {author}.'), author=ctx.author.name))

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.kick.guild.reason', '{success} Kicked {kicked} from this server.\nReason: `{reason}`'), kicked=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.kick.guild.no_reason', '{success} Kicked {kicked} from this server.'), kicked=member.mention))

    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _mute(self, ctx, member: discord.Member, *, reason=None):
        muted_role = discord.utils.get(ctx.guild.roles, name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
        if not muted_role:
            muted_role = await ctx.guild.create_role(name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'), reason=self.msg.get(ctx, 'mod.mute.role.create', 'The muted role didn\'t exist or it was deleted.'))
            for channel in ctx.guild.text_channels:
                perms = discord.PermissionOverwrite()
                perms.send_messages = False
                await channel.set_permissions(muted_role, overwrite=perms)

        if member == ctx.guild.owner or member == self.bot.user or member == ctx.author:
            await ctx.send(self.msg.get(ctx, 'mod.ban.errors.cannot_mute_this_member', '{error} You cannot mute this member!'))
        elif muted_role in member.roles:
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.already_muted', '{error} This user is already muted!'))
        else:
            reason = self.msg.format(self.msg.get(ctx, 'mod.mute.audit.reason', 'Muted by {author}.\nReason: {reason}'), author=ctx.author.name, reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.mute.audit.no_reason', 'Muted by {author}.'), author=ctx.author.name)
            try:
                await member.edit(reason=reason)
            except discord.errors.HTTPException:
                pass

            await member.add_roles(muted_role, reason=reason)

            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.mute.guild.reason', '{success} Muted {muted} by {author}.\nReason: `{user}`'), muted=ctx.author.mention, author=member.mention, user=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.mute.guild.no_reason', '{success} {muted} was muted by {author}.'), muted=member.mention, author=ctx.author.mention))

    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _unmute(self, ctx, member: discord.Member, *, reason=None):
        muted_role = discord.utils.get(ctx.guild.roles, name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
        if muted_role in member.roles:
            reason = self.msg.format(self.msg.get(ctx, 'mod.unmute.audit.reason', 'Unmuted by {author}.\nReason: {reason}'), author=ctx.author.name, reason=reason) if reason else self.msg.format(self.msg.get(ctx, 'mod.unmute.audit.no_reason', 'Unmuted by {author}.'), author=ctx.author.name)
            await member.edit(reason=reason)
            await member.remove_roles(muted_role, reason=reason)
            if reason:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unmute.guild.reason', '{success} {muted} was unmuted.\nReason: `{reason}`'), author=ctx.author.mention, muted=member.mention, reason=reason))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.unmute.guild.no_reason', '{success} {muted} was unmuted by {author}.'), author=ctx.author.mention, muted=member.mention))
        else:
            await ctx.send(self.msg.get(ctx, 'mod.mute.errors.not_muted', '{error} This user isn\'t muted!'))

    @commands.command(name='nickname', aliases=['nick'])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def _nickname(self, ctx, member: discord.Member, *, nickname=None):
        try:
            await member.edit(nick=nickname)
        except discord.errors.Forbidden:
            return await ctx.send(self.msg.get(ctx, 'mod.nickname.errors.cannot_change_nickname', '{error} I can\'t change nickname to that member.'))

        if nickname:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.nickname.changed', '{success} You changed the nickname for **{user}** to `{nickname}`.'), user=member.name, nickname=nickname))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.nickname.removed', '{success} You removed the nickname for **{user}**.'), user=member.name))

    @commands.command(name='announce', aliases=['broadcast', 'bc'])
    @commands.has_permissions(mention_everyone=True)
    @commands.bot_has_permissions(mention_everyone=True)
    async def _announce(self, ctx, *, message):
        await ctx.message.add_reaction('<:athomos_success:600278477421281280>')
        for channel in ctx.guild.text_channels:
            e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'mod.announce.title', 'Announcement'), description=message, timestamp=datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

            try:
                await channel.send(embed=e)
            except:
                pass

    @commands.group(name='report', invoke_without_command=True)
    async def _report(self, ctx, member: discord.Member, *, reason):
        channel = self.mod(ctx.guild).reports_channel
        if channel:
            e = discord.Embed(colour=int('f44336', 16), title=self.msg.get(ctx, 'mod.report.title', 'Report'), timestamp=datetime.utcnow())
            e.add_field(name=self.msg.get(ctx, 'mod.report.reported', 'User reported:'), value=member.mention, inline=False)
            e.add_field(name=self.msg.get(ctx, 'mod.report.reason', 'Reason:'), value=reason, inline=False)
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            try:
                await self.bot.get_channel(channel).send(embed=e)
            except discord.HTTPException:
                await ctx.send(self.msg.get(ctx, 'mod.report.errors.reason_too_long', '{error} **Reasong too long!** Maximum 1024 characters allowed.'))
        else:
            if ctx.author.guild_permissions.manage_guild:
                await ctx.send(self.msg.get(ctx, 'mod.report.channel_not_set.full', '{error} **Reports channel not set!** You can set it with: `{prefix}report set <channel>`.'))
            else:
                await ctx.send(self.msg.get(ctx, 'mod.report.channel_not_set.simple', '{error} **Reports channel not set!** Contact an administrator to configure it.'))

    @_report.command(name='set')
    @commands.has_permissions(manage_guild=True)
    async def _report_set(self, ctx, channel: discord.TextChannel=None):
        mod = self.mod(ctx.guild)
        already_set = mod.reports_channel

        if channel:
            mod.reports_channel = channel.id
        else:
            mod.reports_channel = ctx.channel.id
        self.session.commit()

        channel = self.bot.get_channel(mod.reports_channel).mention
        if already_set:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.report.set.changed', '{success} **Reports channel changed!** Now all reports will be sent to {channel}.'), channel=channel))
        else:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.report.set.new', '{success} **Reports channel configured!** Now all reports will be sent to {channel}.'), channel=channel))

    @_report.command(name='disable')
    @commands.has_permissions(manage_guild=True)
    async def _report_disable(self, ctx):
        mod = self.mod(ctx.guild)
        if mod.reports_channel:
            mod.reports_channel = None
            self.session.commit()
            await ctx.send(self.msg.get(ctx, 'mod.report.remove.disabled', '{success} Reports channel disabled.'))
        else:
            await ctx.send(self.msg.get(ctx, 'mod.report.channel_not_set.full', '{error} **Reports channel not set!** You can set it with: `{prefix}report set <channel>`.'))

    async def purge(self, ctx, limit, all_=True):
        if limit > 2000:
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'mod.clean.too_many_messages', '{error} **Too many messages!** Try a lower number. ({limit}/2000)'), limit=limit))

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
        if ctx.invoked_subcommand is None:
            await self.purge(ctx, limit)

    @_clean.command(name='commands', aliases=['bot', 'command'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _clean_commands(self, ctx, limit: int=25):
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
