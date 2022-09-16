import discord
import itertools
from discord import colour
from discord.ext import commands
from discord.ext.commands.core import Group

from utils.config import Config
from utils.messages import Messages


msg = Messages()


class EmbedPaginator(commands.Paginator):
    def __init__(self, context=None, max_size=2000):
        self.max_size = max_size
        self.ctx = context
        self.prefix = None
        self.clear()

    def clear(self):
        self._current_page = discord.Embed(colour=Config().embeds_color)
        self._count = 0
        self._pages = []

    def add_line(self, line='\u200b', name='\u200b', inline=False, empty=False):
        max_page_size = self.max_size
        if len(line) > max_page_size:
            raise RuntimeError(f'Line exceeds maximum page size {max_page_size}')

        if self._count + len(line) + 1 > self.max_size:
            self.close_page()

        self._count += len(line) + 1
        self._current_page.add_field(name=name, value=line + '\n\u200b' if empty else line, inline=inline)

        if empty:
            self._count += 1

    def close_page(self):
        self._pages.append(self._current_page)
        self._current_page = []
        self._count = 0

    def __repr__(self):
        fmt = '<Paginator max_size: {0.max_size} count: {0._count}>'
        return fmt.format(self)


class BotHelp(commands.DefaultHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)

    def add_indented_commands(self, commands, *, heading, max_size=None):
        if not commands:
            return

        ctx = self.context
        qualified_name = [command.cog.qualified_name for command in commands][0]

        name = '» ' + msg.get(ctx, 'cog_names.' + qualified_name.lower(), heading)
        if heading == msg.get(ctx, 'help.headings.subcommands', 'Subcommands:') or heading == msg.get(ctx, 'help.headings.commands', 'Commands:'):
            name = heading

        self.paginator.add_line(line=', '.join(['`' + self.shorten_text(f'{self.clean_prefix}{command.qualified_name}') + '`' for command in commands]), name=name)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            fmt = command.name
            if parent:
                fmt = '{0} [{1}]'.format(parent, ' | '.join(command.aliases))
            alias = fmt
        else:
            alias = command.name if not parent else parent + ' ' + command.name

        return f'{self.clean_prefix}{alias} {command.signature}'

    def add_command_formatting(self, command):
        signature = self.get_command_signature(command)
        helpText = msg.get(self.context, 'command_descriptions.' + command.qualified_name.lower().replace(' ', '.') + '.desc', command.help if command.help else '')

        note = self.get_ending_note()
        if note:
            self.paginator._current_page.set_footer(text=note)

        signature = signature.replace('subcommand', msg.get(self.context, 'miscellaneous.subcommand', 'Subcommand').lower())
        signature = signature.replace('command', msg.get(self.context, 'miscellaneous.command', 'Command').lower())

        try:
            for key, value in msg.parse('config/i18n/' + msg.get_locale(self.context.guild.id)[0] + '.json')['command_arguments'].items():
                if f'[{key}]' in signature:
                    signature = signature.replace(f'[{key}]', f'[{value}]')
                elif f'[{key}...]' in signature:
                    signature = signature.replace(f'[{key}...]', f'[{value}...]')
                elif f'<{key}>' in signature:
                    signature = signature.replace(f'<{key}>', f'<{value}>')
        except KeyError:
            pass

        self.paginator._current_page.title = signature
        self.paginator._current_page.description = helpText if helpText != '' else msg.get(self.context, 'help.errors.description_not_found', 'This command doesn\'t have a description.')

    def get_ending_note(self, src='bot', ctx=None):
        if src == 'bot':
            return msg.get(self.context, 'help.footer.bot', 'You can use {prefix}help [command | category] for more info on a command or a category.')
        elif src == 'group':
            return msg.format(msg.get(self.context, 'help.footer.group', 'You can use {prefix}help {command} [subcommand] for more info on a subcommand.'), command=ctx.qualified_name)
        elif src == 'cog':
            return msg.get(self.context, 'help.footer.cog', 'You can use {prefix}help [command] for more info on a command.')

    def subcommand_not_found(self, command, string):
        if isinstance(command, Group) and len(command.all_commands) > 0:
            return msg.format(msg.get(self.context, 'help.errors.subcommand_not_found', '{error} The subcommand `{name}` doesn\'t exist.'), name=string)
        return msg.format(msg.get(self.context, 'help.errors.subcommand_not_exist', '{error} The command `{prefix}{command}` doesn\'t have subcommands.'), command=command.qualified_name)

    def command_not_found(self, string):
        return msg.format(msg.get(self.context, 'help.errors.command_not_found', '{error} The command `{prefix}{command}` doesn\'t exist.'), command=string)

    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            await destination.send(embed=page)

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=msg.get(self.context, 'help.headings.subcommands', 'Subcommands:'))

        if filtered:
            note = self.get_ending_note('group', group)
            if note:
                self.paginator._current_page.set_footer(text=note)
        await self.send_pages()

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        self.paginator._current_page.title = msg.format(msg.get(ctx, 'help.bot.title', '{name}\'s Help'), name=bot.user.name)

        no_category = '\u200b{0.no_category}:'.format(self)

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, bot_commands in to_iterate:
            bot_commands = sorted(bot_commands, key=lambda c: c.name) if self.sort_commands else list(bot_commands)
            self.add_indented_commands(bot_commands, heading=category, max_size=max_size)

        if bot.help_links(ctx):
            self.paginator.add_line(' | '.join([f"[{name}]({link})" for name, link in bot.help_links(ctx)]), '\u200b\n» ' + msg.get(ctx, 'help.links.title', 'Links :pushpin:'))

        note = self.get_ending_note()
        if note:
            self.paginator._current_page.set_footer(text=note)
        await self.send_pages()

    async def send_cog_help(self, cog):
        helpText = msg.get(self.context, 'cogs_help', cog.description)
        if len(cog.qualified_name.split()) > 1:
            name = cog.qualified_name.split()
            name.remove('»')
        else:
            name = cog.qualified_name
        self.paginator._current_page.title = msg.format(msg.get(self.context, 'help.cog.title', '{cog_name} Commands'), cog_name=name)
        self.paginator._current_page.description = helpText if helpText != '' else msg.get(self.context, 'help.cog.description_not_found', 'This cog doesn\'t have a description.')

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=msg.get(self.context, 'help.headings.commands', 'Commands:'))

        note = self.get_ending_note('cog')
        if note:
            self.paginator._current_page.set_footer(text=note)

        await self.send_pages()

    async def command_callback(self, ctx, *, command=None):
        self.paginator = EmbedPaginator(context=ctx)

        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        cogs = {name.split()[1].lower() if len(name.split()) > 1 else name.lower(): cog for name, cog in bot.cogs.items()}
        cog = cogs.get(command.lower())
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._original_help_command = self.bot.help_command
        self.bot.help_command = BotHelp(paginator=EmbedPaginator(), verify_checks=False)
        self.bot.help_command.cog = self

    # Functions
    async def intro(self, ctx):
        e = discord.Embed(colour=Config().embeds_color, title=msg.get(ctx, 'help.intro.title', 'Hello there! :wave:'))
        e.description = msg.get(ctx, 'help.intro.description', 'I\'m Athomos, a multi-purpose bot designed to be easy-to-use and user friendly.')
        e.set_footer(text=msg.get(ctx, 'help.intro.footer', 'To start using me, do {prefix}help and see all the available commands.'))
        await ctx.send(embed=e)

    # Events
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user in message.mentions and message.content.replace('!', '').replace(str(self.bot.user.mention), '') == '':
            await self.intro(await self.bot.get_context(message))

    # Commands
    @commands.hybrid_command(name='intro')
    async def cmd_intro(self, ctx):
        """
        Shows the introduction message.
        """
        await self.intro(ctx)
    
    # @commands.command(name='info', aliases=['changelog'])
    # async def cmd_info(self, ctx):
    #     """
    #     Shows some useful information about the bot.
    #     """
    #     e = discord.Embed(colour=Config().embeds_color, title=msg.format(msg.get(ctx, 'help.info.title', 'About {name}'), name=self.bot.user.name))
    #     e.set_thumbnail(url=self.bot.user.avatar_url)

    #     announcements_channel = self.bot.get_channel(Config().announcements_channel)
    #     latest_news_raw = await announcements_channel.fetch_message(announcements_channel.last_message_id)
    #     latest_news = latest_news_raw.clean_content.replace('@here', '').replace('@everyone', '')
    #     e.add_field(name=msg.get(ctx, 'help.info.latest_news', 'Latest news:'), value=(
    #         latest_news[:512] + '... [Continua a leggere](https://discord.gg/ptXUqzU6aF)') if len(latest_news) > 75 else latest_news)

    #     await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(Support(bot))
