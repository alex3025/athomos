
import discord
from discord.ext import menus, commands

from utils.config import Config
from utils.database import Database
from utils.messages import Messages
from utils.paginator import EmbedFieldsPaginator


class CustomCommands(commands.Cog):
    """
    Module containing commands useful for managing customized commands.
    """

    def __init__(self, bot):
        self.bot = bot

        self.msg = Messages()
        self.db = Database().db
        self.config = Config()


    async def cog_check(self, ctx):
        perms = {'manage_messages': True}
        raised_perms = []
        for perm, value in perms.items():
            if getattr(ctx.channel.permissions_for(ctx.author), perm, None) != value:
                raised_perms.append(perm)
        if len(raised_perms) > 0:
            raise commands.MissingPermissions(raised_perms)
        return True


    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author == self.bot.user and message.guild:
            try:
                customCommands = self.db.find_one({'id': message.guild.id})['customCommands']
                for customCommand in customCommands:
                    if list(await self.bot.get_prefix(message))[-1] + customCommand == message.content:
                        if customCommands[customCommand]['type'] == 'text':
                            return await message.channel.send(customCommands[customCommand]['data'].format_map(self.msg.placeholders(message)))
                        # elif customCommand['type'] == 'role':
                        #     await message.author.add_roles(customCommand['data'], reason=f'Added by customcommand: {message.content}')
            except TypeError:
                pass


    # Commands
    @commands.group(name='customcommands', aliases=['cc', 'customcommand'])
    async def _customcommands(self, ctx):
        """
        Show all custom commands for this server.
        """
        if ctx.invoked_subcommand is None:
            fields = [{'**' + list(await self.bot.get_prefix(ctx.message))[-1] + name + '**': attrs['data'].format_map(self.msg.placeholders(ctx.message))} for name, attrs in self.db.find_one({'id': ctx.guild.id})['customCommands'].items()]

            if len(fields) <= 0:
                return await ctx.send(self.msg.get(ctx, 'customcommands.none', '{error} This server doesn\'t have any custom commands. You can add a new one with `{prefix}customcommands add <name> <text>`.'))

            e = discord.Embed(colour=self.config.embeds_color, title=self.msg.get(ctx, 'customcommands.title', 'Custom commands:'))
            pages = menus.MenuPages(source=EmbedFieldsPaginator(embed=e, fields=fields, ctx=ctx, per_page=10), clear_reactions_after=True)
            await pages.start(ctx)


    @_customcommands.command(name='add', aliases=['create'])
    async def _customcommands_add(self, ctx, name, *, text):
        """
        Allows you to create a new custom command.
        """
        if self.bot.get_command(name):
            return await ctx.send(self.msg.get(ctx, 'customcommands.errors.is_bot_command', '{error} You cannot overwrite a bot command.'))

        customCommands = self.db.find_one({'id': ctx.guild.id})['customCommands']
        
        if name not in customCommands:
            self.db.update_one({'id': ctx.guild.id}, {'$set': {f'customCommands.{name}': {'type': 'text', 'data': text}}}, upsert=True)
            await ctx.send(self.msg.format(self.msg.get(ctx, 'customcommands.add.added', '{success} Custom command `{prefix}{name}` created.'), name=name))
        else:
            await ctx.send(self.msg.get(ctx, 'customcommands.errors.already_exist', '{error} That custom command already exist.'))


    @_customcommands.command(name='edit', aliases=['modify', 'update'])
    async def _customcommands_edit(self, ctx, name, *, text):
        """
        Allows to edit a custom command.
        """
        customCommands = self.db.find_one({'id': ctx.guild.id})['customCommands']

        if name in customCommands:
            self.db.update_one({'id': ctx.guild.id}, {'$set': {f'customCommands.{name}.data': text}})
            await ctx.send(self.msg.format(self.msg.get(ctx, 'customcommands.edit.edited', '{success} You edited the `{prefix}{name}` custom command.'), name=name))
        else:
            await ctx.send(self.msg.get(ctx, 'customcommands.errors.not_found', '{error} That custom command doesn\'t exist.'))


    @_customcommands.command(name='remove', aliases=['delete'])
    async def _customcommands_remove(self, ctx, name):
        """
        Allows you to remove a custom command.
        """
        customCommands = self.db.find_one({'id': ctx.guild.id})['customCommands']

        if name in customCommands:
            self.db.update_one({'id': ctx.guild.id}, {'$unset': {f'customCommands.{name}': ""}})
            await ctx.send(self.msg.format(self.msg.get(ctx, 'customcommands.remove.removed', '{success} Custom command `{prefix}{name}` removed.'), name=name))
        else:
            await ctx.send(self.msg.get(ctx, 'customcommands.errors.not_found', '{error} That custom command doesn\'t exist.'))


def setup(bot):
    bot.add_cog(CustomCommands(bot))
