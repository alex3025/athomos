from discord.ext import commands


def no_reply(ctx):
    """
    A simple check that allows to disable the reply to the command invocation.
    """
    return True

class CustomContext(commands.Context):
    async def send(self, *args, **kwargs):
        if self.command.checks is not None:
            if no_reply in self.command.checks if len(self.command.checks) > 0 else False:
                return await super().send(*args, **kwargs)
        return await self.reply(*args, **kwargs, mention_author=False)
