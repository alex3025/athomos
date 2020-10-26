import json
import discord
import sqlalchemy
from discord.ext import menus
from discord.ext import commands

from utils.config import Config
from utils.database import Database
from utils.messages import Messages
from utils.paginator import EmbedPaginator


class CustomCommands(commands.Cog):
    """
    Module containing commands useful for managing customized commands.
    """

    def __init__(self, bot):
        self.bot = bot

        self.msg = Messages()
        self.db = Database()
        self.config = Config()
        self.session = self.db.session

        self.customcommands = lambda guild: self.db.get(self.db.CustomCommands.guild_id == guild.id, self.db.CustomCommands)

        self.placeholders = self.msg.placeholders

    async def cog_check(self, ctx):
        perms = {'manage_messages': True}
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
        self.session.add(self.db.CustomCommands(guild_id=guild.id))
        self.session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            self.session.delete(self.db.get(self.db.CustomCommands.guild_id == guild.id, self.db.CustomCommands))
            self.session.commit()
        except sqlalchemy.orm.exc.UnmappedInstanceError:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot and message.guild:
            for name, text in json.loads(self.customcommands(message.guild).customcommands).items():
                if message.content == list(await self.bot.get_prefix(message))[-1] + name:
                    await message.channel.send(text.format_map(self.placeholders(message)))

    # Commands
    @commands.group(name='customcommands', aliases=['cc', 'customcommand'])
    async def _customcommands(self, ctx):
        """
        Show all custom commands for this server.
        """
        fields = [{'**' + list(await self.bot.get_prefix(ctx.message))[-1] + name + '**': value.format_map(self.placeholders(ctx.message))} for name, value in json.loads(self.customcommands(ctx.guild).customcommands).items()]

        e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'customcommands.title', 'Custom commands:'))
        pages = menus.MenuPages(source=EmbedPaginator(embed=e, fields=fields, ctx=ctx, per_page=5), clear_reactions_after=True)
        await pages.start(ctx)

    @_customcommands.command(name='add', aliases=['create'])
    async def _customcommands_add(self, ctx, name, *, text):
        """
        Allows you to create a new custom command.
        """
        customcommands = self.customcommands(ctx.guild)
        all_cc = json.loads(customcommands.customcommands)

        if self.bot.get_command(name):
            return await ctx.send(self.msg.get(ctx, 'customcommands.add.errors.is_bot_command', '{error} You cannot overwrite a bot command.'))

        if name not in all_cc:
            all_cc[name] = text
            customcommands.customcommands = json.dumps(all_cc)
            self.session.commit()
            await ctx.send(self.msg.format(self.msg.get(ctx, 'customcommands.add.added', '{success} Custom command `{prefix}{name}` created.'), name=name))
        else:
            await ctx.send(self.msg.get(ctx, 'customcommands.add.errors.already_exist', '{error} That custom command already exist.'))

    @_customcommands.command(name='remove', aliases=['delete'])
    async def _customcommands_remove(self, ctx, name):
        """
        Allows you to remove a custom command.
        """
        customcommands = self.customcommands(ctx.guild)
        all_cc = json.loads(customcommands.customcommands)
        if name in all_cc:
            all_cc.pop(name)
            customcommands.customcommands = json.dumps(all_cc)
            self.session.commit()
            await ctx.send(self.msg.format(self.msg.get(ctx, 'customcommands.remove.removed', '{success} Custom command `{prefix}{name}` removed.'), name=name))
        else:
            await ctx.send(self.msg.get(ctx, 'customcommands.remove.errors.not_found', '{error} That custom command doesn\'t exist.'))


def setup(bot):
    bot.add_cog(CustomCommands(bot))
