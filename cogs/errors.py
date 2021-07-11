import sys
import traceback
from discord.ext import commands

from utils.logger import Logger
from utils.messages import Messages


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.msg = Messages()
        self.log = Logger()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        ignored = (commands.CommandNotFound, commands.NoPrivateMessage, commands.CheckFailure)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.BadArgument):
            param = list(ctx.command.clean_params.items())[len(ctx.kwargs)][0]
            text = str(error).split('"')[1]
            if param == 'member' or param == 'user':
                return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.member_not_found', '{error} Member `{member}` not found.'), member=text))
            elif param == 'role' or param == 'roles':
                return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.role_not_found', '{error} Role `{role}` not found!'), role=text))
            elif param == 'textchannel' or param == 'textchannels':
                return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.text_channel_not_found', '{error} Text Channel `{text_channel}` not found!'), text_channel=text))
            else:
                return await ctx.send(self.msg.get(ctx, 'errors.bad_arguments', '{error} **Bad argument(s)!** Check the command.'))

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.missing_argument', '{error} **Syntax error!** Use: `{prefix}{name} {subcommands}`.'), name=ctx.command.qualified_name, subcommands=ctx.command.signature))

        elif isinstance(error, commands.MissingPermissions):
            missing_perms = [self.msg.get(ctx, f'permissions.{perm_name}', perm_name.title().replace('_', ' ')) for perm_name in error.missing_perms]
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.missing_permissions', '{error} **Missing permissions!** To run this command you need these permissions: `{permissions}`.'), permissions=', '.join(missing_perms)))

        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = [self.msg.get(ctx, f'permissions.{perm_name}', perm_name.title().replace('_', ' ')) for perm_name in error.missing_perms]
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'errors.bot_missing_permissions', '{error} **Missing bot permissions!** To run this command I need these permissions: `{permissions}`.'), permissions=', '.join(missing_perms)))

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(self.msg.get(ctx, 'errors.disabled_command', '{error} This command is **disabled** by the bot owner!'))

        elif isinstance(error, commands.NotOwner):
            return await ctx.send(self.msg.get(ctx, 'errors.owner_only', '{error} This command can be **executed only** by the bot owner!'))

        else:
            self.log.error('Ignoring exception in command {}:'.format(ctx.command))
            if self.log.print_traceback():
                traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
