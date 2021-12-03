from discord.ext import commands
from aiohttp import ClientSession
from json.decoder import JSONDecodeError
from discord import FFmpegPCMAudio, VoiceChannel
from discord.ext.commands.errors import CommandError

from utils.logger import Logger
from utils.config import Config
from utils.messages import Messages


class Radio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.log = Logger()
        self.msg = Messages()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is not None and member.guild.voice_client:
            if before.channel == member.guild.voice_client.channel and len(before.channel.members) == 1:
                await member.guild.voice_client.disconnect()

    @commands.command(name='connect', aliases=['play'])
    async def cmd_connect(self, ctx):
        if not ctx.voice_client.is_playing():
            async with ctx.typing():
                await ctx.invoke(self.cmd_playing)
                ctx.voice_client.play(FFmpegPCMAudio('http://192.168.1.33:8000/stream'), after=lambda e: self.log.exception(f'Player error: {e}') if e else None)

    
    @commands.command(name='stop', aliases=['dc', 'disconnect'])
    async def cmd_stop(self, ctx):
        if ctx.author.voice is not None:
            if ctx.voice_client:
                if ctx.author.voice.channel == ctx.voice_client.channel:
                    if ctx.voice_client is not None:
                        await ctx.message.add_reaction('⏹️')
                        return await ctx.voice_client.disconnect()
            else:
                raise CommandError(self.msg.get(ctx, 'music.errors.not_connected', '{error} I\'m not connected to a voice channel!'))
        raise CommandError(ctx.send(self.msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!')))

    
    @commands.command(name='playing', aliases=['np', 'nowplaying'])
    async def cmd_playing(self, ctx):
        async with ClientSession() as session:
            async with session.get('http://192.168.1.33:8000/status-json.xsl') as resp:
                name = 'Sconosciuto'
                try:
                    data = await resp.json()
                    name = data["icestats"]["source"]["title"]
                except JSONDecodeError:
                    pass
                finally:
                    await ctx.send(f':christmas_tree: **In riproduzione:** `{name.strip()}`')

    @cmd_connect.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                await ctx.send(f'<:athomos_success:600278477421281280> **Connesso a {ctx.author.voice.channel.mention}!**')
            else:
                raise CommandError(self.msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))


def setup(bot):
    bot.add_cog(Radio(bot))
