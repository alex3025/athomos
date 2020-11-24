import os
import discord
import sqlalchemy
from discord.ext import commands

from utils.config import Config
from utils.logger import Logger
from utils.database import Database
from utils.messages import Messages


class Admin(commands.Cog):
    """
    Module containing commands useful for configuring the bot.
    """

    def __init__(self, bot):
        self.bot = bot

        self.msg = Messages()
        self.db = Database()
        self.log = Logger()
        self.config = Config()
        self.session = self.db.session

        self.admin = lambda guild: self.db.get(self.db.Admin.guild_id == guild.id, self.db.Admin)

    async def cog_check(self, ctx):
        perms = {'manage_guild': True}
        raised_perms = []
        for perm, value in perms.items():
            if getattr(ctx.channel.permissions_for(ctx.author), perm, None) != value:
                raised_perms.append(perm)
        if len(raised_perms) > 0:
            raise commands.MissingPermissions(raised_perms)
        return True

    # Events
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.session.add(self.db.Admin(guild_id=guild.id))
        self.session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            self.session.delete(self.admin(guild))
            self.session.commit()
        except sqlalchemy.orm.exc.UnmappedInstanceError:
            pass

    # Commands
    @commands.group(name='settings', aliases=['setting'])
    async def _settings(self, ctx):
        """
        Allows you to manage the bot settings.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @_settings.command(name='prefix')
    async def _prefix(self, ctx, prefix):
        """
        Allows you to change the bot prefix.
        """
        max_length = 4
        guild = self.db.get(self.db.Guild.guild_id == ctx.guild.id)
        if '@' in prefix or '#' in prefix or '/' in prefix:
            await ctx.send(self.msg.get(ctx, 'admin.settings.prefix.errors.bad_prefix', '{error} Prefix can\'t contain `#`, `@` or `/` characters.'))
        elif len(prefix) > max_length:
            await ctx.send(self.msg.format(self.msg.get(ctx, 'admin.settings.prefix.errors.too_long', '{error} Prefix can\'t be longer than {length} characters.'), length=max_length))
        else:
            guild.prefix = prefix
            self.session.commit()
            await ctx.send(self.msg.get(ctx, 'admin.settings.prefix.updated', '{success} **Prefix changed!** Now the prefix is: `{prefix}`'))

    @_settings.command(name='language', aliases=['lang'])
    @commands.is_owner()
    @commands.bot_has_permissions(manage_roles=True)
    async def _language(self, ctx, *, language=None):
        """
        Allows you to change the language of the bot.
        """
        avaiable_languages = {}
        for lang in os.listdir('config/i18n/'):
            lang_file = self.msg.parse('config/i18n/' + lang)
            if lang.replace('.json', '') == self.bot.current_lang(ctx.message):
                lang_split = lang_file['language_name'].split(' ')
                lang_split[1] = '**' + lang_split[1] + '**'
                avaiable_languages[lang.replace('.json', '')] = ' '.join(lang_split)
            else:
                avaiable_languages[lang.replace('.json', '')] = lang_file['language_name']

        if language is None:
            prefix = list(await self.bot.get_prefix(ctx.message))[-1]
            e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'admin.settings.language.title', 'Language Settings'), description=f'`{prefix}{ctx.command.qualified_name} {ctx.command.signature}`')
            e.add_field(name=self.msg.get(ctx, 'admin.settings.language.available_languages', 'Available languages'), value=', '.join(avaiable_languages.values()), inline=True)
            await ctx.send(embed=e)
        else:
            guild = self.db.get(self.db.Guild.guild_id == ctx.guild.id)
            muted_role = discord.utils.get(ctx.guild.roles, name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
            old_lang = guild.language
            for lang_code, lang_name in avaiable_languages.items():
                lang_lower = lang_name.split(' ')
                lang_lower.remove(lang_lower[0])
                if language.lower() == ''.join(lang_lower).lower():
                    new_lang_name = lang_name
                    guild.language = lang_code
                    self.session.commit()
                    await muted_role.edit(name=self.msg.get(ctx, 'mod.mute.role.name', 'Muted'))
            if guild.language == old_lang:
                await ctx.send(self.msg.get(ctx, 'admin.settings.language.errors.not_exist', '{error} **That language isn\'t avaiable!** See all the languages avaiable with: `{prefix}setting language`'))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'admin.settings.language.updated', '{success} **Language changed!** Now the bot\'s language for this server is: **{language}**'), language=new_lang_name))

    @_settings.group(name='messages', aliases=['msg', 'message'])
    async def _messages(self, ctx):
        """
        Allows you to manage the settings for join and leave messages.
        """
        if ctx.invoked_subcommand is None:
            admin = self.admin(ctx.guild)
            e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'admin.settings.messages.title', 'Messages'))

            join_message = admin.join_message.format_map(self.msg.placeholders(ctx.message)) if admin.join_message else None
            leave_message = admin.leave_message.format_map(self.msg.placeholders(ctx.message)) if admin.leave_message else None

            e.add_field(name=self.msg.get(ctx, 'admin.settings.messages.join_message.title.title', '**Join Message** (JM)'), value=(join_message[:64] + '...' if len(join_message) > 64 else join_message) if join_message else self.msg.get(ctx, 'admin.settings.messages.join_message.title.disabled', 'Join Message isn\'t set.'), inline=True)
            e.add_field(name=self.msg.get(ctx, 'admin.settings.messages.join_message.text_channel.title', '**JM** Text Channel'), value=f'<#{admin.join_message_textChannel}>' if admin.join_message_textChannel else self.msg.get(ctx, 'admin.settings.messages.join_message.text_channel.disabled', '{error} Not set'), inline=True)
            e.add_field(name=self.msg.get(ctx, 'admin.settings.messages.join_message.send_in_dm', '**JM** Send in DM'), value=f"<:athomos_success:600278477421281280> {self.msg.get(ctx, 'miscellaneous.enabled', 'Enabled')}" if admin.join_message_sendInDM else f"<:athomos_error:600278499055370240> {self.msg.get(ctx, 'miscellaneous.disabled', 'Disabled')}", inline=True)

            e.add_field(name=self.msg.get(ctx, 'admin.settings.messages.leave_message.title.title', '**Leave Message** (LM)'), value=(leave_message[:64] + '...' if len(leave_message) > 64 else leave_message) if leave_message else self.msg.get(ctx, 'admin.settings.messages.leave_message.title.disabled', 'Leave Message isn\'t set.'), inline=True)
            e.add_field(name=self.msg.get(ctx, 'admin.settings.messages.leave_message.text_channel.title', '**LM** Text Channel'), value=f'<#{admin.leave_message_textChannel}>' if admin.leave_message_textChannel else self.msg.get(ctx, 'admin.settings.messages.leave_message.text_channel.disabled', '{error} Not set'), inline=True)
            e.add_field(name='\u200b', value='\u200b', inline=True)  # Spacer

            e.set_footer(text=self.msg.get(ctx, 'admin.settings.messages.footer', 'You can customize these messages using placeholders.\nSee them with: {prefix}settings messages placeholders'))

            await ctx.send(embed=e)

    @_messages.command(name='placeholders', aliases=['ph'])
    async def _messages_placeholders(self, ctx):
        """
        Shows placeholders that can be used to customize join, leave, and custom commands.
        """
        e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'admin.settings.messages.placeholders.title', 'Messages Placeholders'), description='1. `{JoinedAtDate}` - ' + f"({ctx.author.joined_at.strftime('%d/%m/%Y')})\n" + '2. `{JoinedAtTime}` - ' + f"({ctx.author.joined_at.strftime('%H:%M')})\n" + '3. `{Mention}` - ' + f"({ctx.author.mention})\n" + '4. `{Username}` - ' + f"({ctx.author.name})\n" + '5. `{ServerName}` - ' + f"({ctx.guild.name})\n" + '6. `{ServerMembersCount}` - ' + f"({len(ctx.guild.members)})")
        e.set_footer(text=self.msg.get(ctx, 'admin.settings.messages.placeholders.footer', 'You can use these placeholders to customize messages.'))
        await ctx.send(embed=e)

    @_messages.group(name='join', invoke_without_command=True, case_insensitive=True)
    async def _messages_join(self, ctx, *, welcome_message):
        """
        Allows you to configure the join message.
        """
        if ctx.invoked_subcommand is None:
            admin = self.admin(ctx.guild)

            already_exist = admin.join_message
            admin.join_message = welcome_message
            if not admin.join_message_textChannel:
                admin.join_message_textChannel = ctx.channel.id
            self.session.commit()

            if already_exist:
                await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.title.updated', '{success} **Welcome message updated!**'))
            else:
                await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.title.created', '{success} **Welcome message configured!**'))

            main_command = ctx.command.parent
            await main_command(ctx)

    @_messages_join.command(name='channel')
    async def _messages_join_textChannel(self, ctx, text_channel: discord.TextChannel=None):
        """
        Allows you to set or modify the text channel where the join messages will be sent.
        """
        admin = self.admin(ctx.guild)

        if admin.join_message:
            admin.join_message_textChannel = ctx.message.channel.id if text_channel is None else text_channel.id
            self.session.commit()
        else:
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.errors.disabled', '{error} **Welcome message isn\'t configured!** You can set it with: `{prefix}settings messages join [welcome message]`'))

        main_command = ctx.command.parent.parent
        await main_command(ctx)

    @_messages_join.command(name='sendInDm')
    async def _messages_join_sendInDm(self, ctx):
        """
        Allows you to choose whether to send the welcome message in DMs or in a text channel.
        """
        admin = self.admin(ctx.guild)
        if admin.join_message:
            if admin.join_message_sendInDM:
                admin.join_message_sendInDM = False
            else:
                admin.join_message_sendInDM = True
            self.session.commit()

            main_command = ctx.command.parent.parent
            await main_command(ctx)
        else:
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.errors.disabled', '{error} **Welcome message isn\'t configured!** You can set it with: `{prefix}settings messages join [welcome message]`'))

    @_messages_join.command(name='remove', aliases=['clear', 'delete'])
    async def _messages_join_remove(self, ctx):
        """
        Allows you to remove the join message.
        """
        admin = self.admin(ctx.guild)
        already_exist = admin.join_message
        if already_exist:
            admin.join_message = None
            admin.join_message_textChannel = None
            admin.join_message_sendInDM = False
            self.session.commit()
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.removed', '{success} **Welcome message removed!**'))
        else:
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.join.errors.disabled', '{error} **Welcome message isn\'t configured!** You can set it with: `{prefix}settings messages join [welcome message]`'))

    @_messages.group(name='leave', invoke_without_command=True, case_insensitive=True)
    async def _messages_leave(self, ctx, *, leave_message):
        """
        Allows you to configure the leave message.
        """
        if ctx.invoked_subcommand is None:
            admin = self.admin(ctx.guild)

            already_exist = admin.leave_message
            admin.leave_message = leave_message
            if not admin.leave_message_textChannel:
                admin.leave_message_textChannel = ctx.channel.id
            self.session.commit()

            if already_exist:
                await ctx.send(self.msg.get(ctx, 'admin.settings.messages.leave.title.updated', '{success} **Leave message updated!**'))
            else:
                await ctx.send(self.msg.get(ctx, 'admin.settings.messages.leave.title.created', '{success} **Leave message configured!**'))

            main_command = ctx.command.parent
            await main_command(ctx)

    @_messages_leave.command(name='channel')
    async def _messages_leave_textChannel(self, ctx, text_channel: discord.TextChannel=None):
        """
        Allows you to set or modify the text channel where the leave messages will be sent.
        """
        admin = self.admin(ctx.guild)

        if admin.leave_message:
            admin.leave_message_textChannel = ctx.message.channel.id if text_channel is None else text_channel.id
            self.session.commit()

            main_command = ctx.command.parent.parent
            await main_command(ctx)
        else:
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.leave.errors.disabled', '{error} **Leave message isn\'t configured!** You can set it with: `{prefix}settings messages leave [leave message]`'))

    @_messages_leave.command(name='remove', aliases=['clear', 'delete'])
    async def _messages_leave_remove(self, ctx):
        """
        Allows you to remove the leave message.
        """
        admin = self.admin(ctx.guild)
        already_exist = admin.leave_message
        if already_exist:
            admin.leave_message = None
            admin.leave_message_textChannel = None
            self.session.commit()
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.leave.remove.removed', '{success} **Leave message removed!**'))
        else:
            await ctx.send(self.msg.get(ctx, 'admin.settings.messages.leave.errors.disabled', '{error} **Leave message isn\'t configured!** You can set it with: `{prefix}settings messages leave [leave message]`'))

    @_settings.group(name='joinroles', aliases=['joinrole', 'jr'], invoke_without_command=True)
    async def _joinroles(self, ctx):
        """
        Allows you to configure the roles that will be given when a new user joins the server.
        """
        if ctx.invoked_subcommand is None:
            admin = self.admin(ctx.guild)
            if admin.welcome_roles:
                roles = [ctx.message.guild.get_role(int(role)).mention for role in admin.welcome_roles.split(' ')]
                await ctx.send(embed=discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'admin.settings.joinroles.title', 'Welcome Roles'), description=', '.join(roles)))
            else:
                await ctx.send(self.msg.get(ctx, 'admin.settings.joinroles.errors.disabled', '{error} **Welcome roles are\'t configured!** You can set them with: `{prefix}setting joinroles add <role(s)>`'))

    @_joinroles.command(name='add')
    async def _joinroles_add(self, ctx, *roles: discord.Role):
        """
        Allows you to add one or more roles to the list of joinroles.
        """
        admin = self.admin(ctx.guild)
        if roles == ():
            class Param:
                name = self.msg.get(ctx, 'args.roles', 'roles')
            raise commands.MissingRequiredArgument(Param)
        intersection = set(admin.welcome_roles.split(' ')).intersection(set([str(role.id) for role in roles]))
        if len(list(intersection)) > 0:
            if len(list(intersection)) > 1:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.errors.already_exist.multi', '{error} Roles {roles} are already welcome roles!'), roles=', '.join([ctx.message.guild.get_role(int(role)).mention for role in list(intersection)]))
            else:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.errors.already_exist.single', '{error} Role {role} is already a welcome role!'), role=', '.join([ctx.message.guild.get_role(int(role)).mention for role in list(intersection)]))
            await ctx.send(message)
        elif ctx.guild.default_role in roles:
            await ctx.send(self.msg.get(ctx, 'admin.settings.joinroles.errors.cannot_add_everyone', '{error} You cannot add the `@everyone` role to welcome roles.'))
        else:
            admin.welcome_roles = ' '.join(list(dict.fromkeys([str(role.id) for role in roles] + admin.welcome_roles.split(' ')))).rstrip()
            self.session.commit()
            if len([str(role.id) for role in roles]) > 1:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.added.multi', '{success} Roles {roles} added to welcome roles!'), roles=', '.join([str(role.mention) for role in roles]))
            else:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.added.single', '{success} Role {role} added to welcome roles!'), role=', '.join([str(role.mention) for role in roles]))
            await ctx.send(message)

    @_joinroles.command(name='remove', aliases=['rm'])
    async def _joinroles_remove(self, ctx, *roles: discord.Role):
        """
        Allows you to remove one or more roles from the list of joinroles.
        """
        admin = self.admin(ctx.guild)
        if roles == ():
            class Param:
                name = self.msg.get(ctx, 'args.roles', 'roles')
            raise commands.MissingRequiredArgument(Param)
        intersection = set(admin.welcome_roles.split(' ')).intersection(set([str(role.id) for role in roles]))
        if not len(list(intersection)) > 0:
            if len(list(intersection)) > 1:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.errors.not_exist.multi', '{error} Roles {roles} aren\'t welcome roles!'), roles=', '.join([str(role.mention) for role in roles]))
            else:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.errors.not_exist.single', '{error} Role {role} isn\'t a welcome role!'), role=', '.join([str(role.mention) for role in roles]))
            await ctx.send(message)
        else:
            admin.welcome_roles = ' '.join([i for i in admin.welcome_roles.split(' ') if i not in list(dict.fromkeys([str(role.id) for role in roles]))]).rstrip()
            self.session.commit()
            if len([str(role.id) for role in roles]) > 1:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.removed.multi', '{success} Roles {roles} removed from welcome roles!'), roles=', '.join([str(role.mention) for role in roles]))
            else:
                message = self.msg.format(self.msg.get(ctx, 'admin.settings.joinroles.removed.single', '{success} Role {role} removed from welcome roles!'), role=', '.join([str(role.mention) for role in roles]))
            await ctx.send(message)


def setup(bot):
    bot.add_cog(Admin(bot))
