import datetime
from discord.ext import commands
from aiohttp import ClientSession
from discord import FFmpegPCMAudio, VoiceChannel, Embed
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

    @commands.hybrid_group(name='radio', fallback='play')
    async def cmd_connect(self, ctx):
        """
        Si collega al tuo canale vocale e inizia a riprodurre la radio natalizia!
        """
        if not ctx.voice_client.is_playing():
            await ctx.invoke(self.cmd_playing)
            ctx.voice_client.play(FFmpegPCMAudio('https://azuracast.masterplex.eu/listen/christmas/discord.ogg'), after=lambda e: self.log.exception(f'Player error: {e}') if e else None)

    
    @cmd_connect.command(name='disconnect', aliases=['dc', 'leave', 'stop'])
    async def cmd_stop(self, ctx):
        """
        Interrompe la riproduzione della radio natalizia e si disconnette dal canale vocale.
        """
        if ctx.author.voice is not None:
            if ctx.voice_client:
                if ctx.author.voice.channel == ctx.voice_client.channel:
                    if ctx.voice_client is not None:
                        await ctx.voice_client.disconnect()
                        await ctx.send(f'⏹️ Disconnesso da **{ctx.author.voice.channel.name}**!')
            else:
                raise CommandError(self.msg.get(ctx, 'music.errors.not_connected', '{error} I\'m not connected to a voice channel!'))
        else:
            raise CommandError(self.msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

    
    @cmd_connect.command(name='info', aliases=['playing', 'nowplaying'])
    async def cmd_playing(self, ctx):
        """
        Mostra la canzone in riproduzione attualmente nella radio natalizia.
        """
        async with ClientSession() as session:
            async with session.get('https://azuracast.masterplex.eu/api/nowplaying/christmas') as resp:
                try:
                    data = await resp.json()

                    now_playing = data['now_playing']
                    
                    e = Embed(title=':christmas_tree: **In riproduzione:**', description=f'{data["now_playing"]["song"]["text"]}', color=self.config.embeds_color, url=data['station']['public_player_url'])
                    e.add_field(name='Durata:', value=f'{str(datetime.timedelta(seconds=now_playing["elapsed"]))[2:]} / **{str(datetime.timedelta(seconds=now_playing["duration"]))[2:]}**', inline=True)
                    e.set_thumbnail(url=now_playing['song']['art'])
                    e.set_footer(text='MasterPlex Christmas Radio')

                    await ctx.send(embed=e)
                except Exception as e:
                    self.log.exception(f'Error while getting now playing: {e}')
                    return

    @cmd_connect.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                await ctx.channel.send(f'<:athomos_success:600278477421281280> **Connesso a {ctx.author.voice.channel.mention}!**')
            else:
                raise CommandError(self.msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))


async def setup(bot):
    await bot.add_cog(Radio(bot))
