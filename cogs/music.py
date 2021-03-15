import discord
import asyncio
import datetime
import functools
import itertools
import youtube_dl
from discord.ext import menus
from discord.ext import commands
from async_timeout import timeout

from utils.config import Config
from utils.messages import Messages
from utils.paginator import EmbedPaginator


youtube_dl.utils.bug_reports_message = lambda: ''

msg = Messages()
config = Config()


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    def __init__(self, ctx, search):
        super(YTDLError, self).__init__(msg.format(msg.get(ctx, 'music.errors.not_found', '{error} No results found for: `{search}`.'), search=search))


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.ctx = ctx
        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.is_live = data.get('is_live')
        self.duration = data.get('duration')

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(ctx, search)

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(ctx, search)

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)

        try:
            processed_info = await loop.run_in_executor(None, partial)
        except youtube_dl.utils.DownloadError:
            raise YTDLError(ctx, search)

        if processed_info is None:
            raise YTDLError(ctx, search)

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError(ctx, search)

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)


class Song:
    __slots__ = ('source', 'requester', 'duration', 'ctx')

    def __init__(self, source: YTDLSource):
        self.ctx = source.ctx
        self.source = source
        self.requester = source.requester
        self.duration = lambda ctx: str(datetime.timedelta(seconds=source.duration)).lstrip('0').replace(' 0', ' ').lstrip(':') if not source.is_live else msg.get(ctx, 'music.play.live', '**LIVE** :red_circle:')

    def enqueued_embed(self, ctx):
        e = discord.Embed(colour=config.embeds_color, title=msg.format(msg.get(ctx, 'music.play.title', '{success} Song added to the queue! [{position}]'), position=len(ctx.voice_state.songs) if not ctx.voice_state.voice.is_playing() else len(ctx.voice_state.songs) + 1))

        e.set_thumbnail(url=self.source.thumbnail)

        e.add_field(name=msg.get(ctx, 'music.play.song_title', 'Title:'), value='[{0}]({1})'.format(self.source.title, self.source.webpage_url), inline=True)
        e.add_field(name=msg.get(ctx, 'music.play.requester', 'Requested by:'), value=self.requester.mention, inline=True)
        e.add_field(name=msg.get(ctx, 'music.play.uploader', 'Uploaded by:'), value='[{0}]({1})'.format(self.source.uploader, self.source.uploader_url), inline=False)
        e.add_field(name=msg.get(ctx, 'music.play.duration', 'Duration:'), value=self.duration(ctx), inline=False)

        return e

    def __str__(self):
        return msg.format(msg.get(self.ctx, 'music.now_playing', '**Now playing:** `{title}` requested by {requester}.'), title=self.source.title, requester=self.requester.mention)


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

        if self.voice:
            self.voice.source.volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            # self.next.clear()

            if not self.loop:
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)

            await self.current.source.channel.send(str(self.current))

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    """
    Module containing commands dedicated to the music function.
    """

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(name='summon', aliases=['join'])
    async def _summon(self, ctx, *, channel: discord.VoiceChannel=None):
        """
        Allows you to invoke the bot in the current voice channel.
        """
        if channel is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                return await ctx.send(msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

        if ctx.voice_state.voice:
            if ctx.voice_state.voice.channel == channel:
                return await ctx.send(msg.get(ctx, 'music.errors.same_channel', '{error} I\'m already connected to that channel!'))
            return await ctx.voice_state.voice.move_to(channel)

        ctx.voice_state.voice = await channel.connect()
        await ctx.send(msg.format(msg.get(ctx, 'music.summon.connected', '{success} Connected to **{channel}**!'), channel=channel))

    @commands.command(name='stop', aliases=['disconnect', 'leave', 'dc'])
    async def _stop(self, ctx):
        """
        Allows you to stop playback.
        """
        if ctx.voice_state.voice:
            await ctx.voice_state.stop()
            del self.voice_states[ctx.guild.id]
            await ctx.message.add_reaction('⏹')
        else:
            await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))

    @commands.command(name='volume', aliases=['vol'])
    async def _volume(self, ctx, *, volume: int=None):
        """
        Allows you to view, raise or lower the volume.
        """

        if not ctx.voice_state.voice:
            return await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))
        if not ctx.author.voice:
            return await ctx.send(msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

        current_volume = ctx.voice_state.volume

        if volume is None:
            current_volume_rounded = int(current_volume * 100)
            if current_volume_rounded == 0:
                string = msg.get(ctx, 'music.volume.current.muted', '🔇 Current volume is **{volume}%**.')
            elif current_volume_rounded <= 100:
                string = msg.get(ctx, 'music.volume.current.low', '🔉 Current volume is **{volume}%**.')
            else:
                string = msg.get(ctx, 'music.volume.current.high', '🔊 Current volume is **{volume}%**.')
            return await ctx.send(msg.format(string, volume=current_volume_rounded))

        if volume / 100 == ctx.voice_state.volume:
            return await ctx.send(msg.format(msg.get(ctx, 'music.volume.same', '{error} Volume is already set to **{volume}%**.'), volume=volume))

        if ctx.author.guild_permissions.administrator:
            if volume > 200 or volume < 0:
                return await ctx.send(msg.get(ctx, 'music.volume.not_valid', '{error} Volume must be between **0** and **200**!'))

            new_volume = volume / 100
            ctx.voice_state.volume = new_volume

            if current_volume < new_volume:
                await ctx.send(msg.format(msg.get(ctx, 'music.volume.raised', '{success} Volume raised to **{level}%**.'), level=volume))
            else:
                await ctx.send(msg.format(msg.get(ctx, 'music.volume.down', '{success} Volume down to **{level}%**.'), level=volume))
        else:
            raise commands.MissingPermissions(['administrator'])

    @commands.command(name='now', aliases=['nowplaying', 'playing', 'np'])
    async def _now_playing(self, ctx):
        """
        Allows you to view the song that is being played.
        """
        if ctx.voice_state.current:
            await ctx.send(str(ctx.voice_state.current))
        else:
            return await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))

    @commands.command(name='pause')
    async def _pause(self, ctx):
        """
        Allows you to pause playback.
        """
        if ctx.voice_state.voice:
            if ctx.voice_state.voice.is_playing():
                ctx.voice_state.voice.pause()
                return await ctx.message.add_reaction('⏸️')
        return await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))

    @commands.command(name='resume')
    async def _resume(self, ctx):
        """
        Allows you to resume playback.
        """
        if ctx.voice_state.voice:
            if ctx.voice_state.voice.is_paused():
                ctx.voice_state.voice.resume()
                await ctx.message.add_reaction('▶️')        
            else:
                await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))
        else:
            await ctx.send(msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

    @commands.command(name='skip')
    async def _skip(self, ctx):
        """
        Allows you to vote to skip the current song.

        If you have requested the current song, you can immediately skip without a vote.
        """
        if ctx.voice_state:
            if not ctx.voice_state.is_playing:
                return await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))
        else:
            return await ctx.send(msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

        voter = ctx.message.author
        skipped = False
        if voter == ctx.voice_state.current.requester:
            skipped = True
            ctx.voice_state.skip()
        elif voter.guild_permissions.administrator:
            skipped = True
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                skipped = True
                ctx.voice_state.skip()
            else:
                await ctx.send(msg.format(msg.get(ctx, 'music.skip.vote_added', '{success} Skip vote added! Currently at **{votes}/3**.'), votes=total_votes))

        else:
            await ctx.send(msg.get(ctx, 'music.skip.already_voted', '{error} You have already voted to skip this song.'))

        if skipped:
            await ctx.message.add_reaction('⏭')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx,):
        """
        Allows you to view the songs in the queue.
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(msg.get(ctx, 'music.queue.empty', '{error} The queue is empty.'))

        fields = []
        counter = 1
        for song in ctx.voice_state.songs:
            fields.append({f'{counter}. **{song.source.title}** [{song.duration(ctx)}]': msg.format(msg.get(ctx, 'music.queue.requester', 'Requested by {requester}'), requester=song.requester.mention)})
            counter += 1

        e = discord.Embed(colour=config.embeds_color, title=msg.get(ctx, 'music.queue.title', 'Music Queue:'))
        pages = menus.MenuPages(source=EmbedPaginator(embed=e, fields=fields, ctx=ctx, per_page=10), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.command(name='remove')
    async def _remove(self, ctx, index: int):
        """
        Allows you to remove a song from the queue.
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(msg.get(ctx, 'music.queue.empty', '{error} The queue is empty.'))

        removed = ctx.voice_state.songs[index - 1]

        if ctx.author == removed.requester or ctx.author.guild_permissions.administrator:
            ctx.voice_state.songs.remove(index - 1)
            await ctx.send(msg.format(msg.get(ctx, 'music.remove.removed', '{success} Removed `{removed}` from queue.'), removed=removed.source.title))
        else:
            await ctx.send(msg.get(ctx, 'music.remove.cannot_remove_other', '{error} You can remove only songs requested by you.'))

    # @commands.command(name='repeat')
    # async def _repeat(self, ctx):
    #     if not ctx.voice_state.is_playing:
    #         return await ctx.send(msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything.'))

    #     ctx.voice_state.loop = not ctx.voice_state.loop

    #     if ctx.voice_state.loop:
    #         await ctx.send(msg.get(ctx, 'music.repeat.repeating', '🔁 Repeating!'))
    #     else:
    #         await ctx.send(msg.get(ctx, 'music.repeat.repeating', '▶️ No longer repeating!'))

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx, *, search: str=None):
        """
        Allows you to play a song.

        You can provide a url or title of the song.
        """
        if search:
            async with ctx.typing():
                try:
                    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                except YTDLError as error:
                    await ctx.send(error)
                # except:
                #     await ctx.send(msg.get(ctx, 'music.play.error', '{error} There was an error, please contact the bot owner.'))
                else:
                    song = Song(source)

                    if not ctx.voice_state.voice:
                        await ctx.invoke(self._summon)

                    await ctx.voice_state.songs.put(song)
                    await ctx.send(embed=song.enqueued_embed(ctx))
        elif ctx.voice_state.voice and ctx.voice_state.voice.is_paused() and search is None:
            await ctx.invoke(self._resume)
        else:
            class Param:
                name = msg.get(ctx, 'command_arguments.search', 'search')
            raise commands.MissingRequiredArgument(Param)

    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.send(msg.get(ctx, 'music.errors.bot_already_connected', '{error} I\'m already connected to a voice channel!'))


def setup(bot):
    bot.add_cog(Music(bot))
