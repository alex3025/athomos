import re
import discord
import lavalink
from discord.ext import commands
from discord.ext import menus
from discord.ext import tasks

from utils.logger import Logger
from utils.config import Config
from utils.messages import Messages
from utils.paginator import EmbedDescriptionPaginator


url_rx = re.compile(r'https?://(?:www\.)?.+')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.config = Config()
        self.msg = Messages()
        self.log = Logger()


    # Functions
    def get_player(self, guild_id):
        return self.lavalink.player_manager.get(guild_id)

    def parse_time(self, time):
        formatted_time = lavalink.format_time(time)

        if formatted_time.startswith('00:'):
            formatted_time = formatted_time[3:]

        return formatted_time

    async def ensure_voice(self, ctx):
        try:
            player = self.lavalink.player_manager.create(
                ctx.guild.id, endpoint=str(ctx.guild.region))
        except lavalink.NodeException:
            self.log.error(
                'A song was requested but there\'s no available nodes!')
            await ctx.send(self.msg.get(ctx, 'music.errors.no_available_nodes', '{error} No available nodes!'))
            return False

        should_connect = self.require_join.__func__ in ctx.command.checks if len(
            ctx.command.checks) > 0 else False

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(self.msg.get(ctx, 'music.errors.user_not_connected', '{error} You aren\'t connected to a voice channel!'))
            return False

        if not player.is_connected:
            if not should_connect:
                await ctx.send(self.msg.get(ctx, 'music.errors.not_connected', '{error} I\'m not connected to a voice channel!'))
                return False

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:
                missing_permissions = {}
                if not permissions.connect:
                    missing_permissions['connect'] = True
                if not permissions.speak:
                    missing_permissions['speak'] = True

                raise commands.BotMissingPermissions(missing_permissions)

            player.store('channel', ctx.channel.id)
            await ctx.guild.change_voice_state(channel=ctx.author.voice.channel)

            # TODO: quando si smuta manualmente il bot, la riproduzione crasha
            # if ctx.guild.me.guild_permissions.deafen_members:
            #     await ctx.guild.me.edit(deafen=True)
        else:
            if player.is_connected and ctx.author.voice.channel.id != int(player.channel_id):
                await ctx.send(self.msg.get(ctx, 'music.errors.not_same_channel', '{error} You need to be in my same voice channel!'))
                return False

        return True


    # Checks
    def require_join(self):
        def predicate(ctx):
            return True
        return commands.check(predicate)

    def is_playing(self):
        async def predicate(ctx):
            if not self.get_player(ctx.guild.id).is_playing:
                await ctx.send(self.msg.get(ctx, 'music.errors.not_playing', '{error} I\'m not playing anything!'))
                return False
            return True
        return commands.check(predicate)


    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self.bot, 'lavalink'):
            self.lavalink = lavalink.Client(self.bot.user.id)
            
            for node in self.config.lavalink_nodes:
                self.lavalink.add_node(node['address'], node['port'], node['password'], node['region'], node['name'])

            self.bot.add_listener(self.lavalink.voice_update_handler, 'on_socket_response')

        self.lavalink.add_event_hook(self.lavalink_event_hook)

    async def cog_check(self, ctx):
        return await self.ensure_voice(ctx)

    def cog_unload(self):
        self.lavalink._event_hooks.clear()

    # TODO: Sistemare sta roba del timeout del bot di quando finisce di riprodurre.
    async def lavalink_event_hook(self, event):
        if isinstance(event, lavalink.TrackStartEvent):  # On playing
            event.player.delete('skip_votes')
        if isinstance(event, lavalink.QueueEndEvent):  # On queue empty
            guild = self.bot.get_guild(int(event.player.guild_id))
            await guild.change_voice_state(channel=None)


    # Commands
    @commands.command(name='play', aliases=['p'])
    @commands.check(require_join)
    async def cmd_play(self, ctx, *, query: str = None):
        """
        Plays a track.
        Valid services: YouTube, Bandcamp, SoundCloud, Twitch, Vimeo and direct resources.

        You can provide the title or the URL.
        """
        player = self.get_player(ctx.guild.id)

        if query == None:
            if player.paused:
                return await ctx.invoke(self.cmd_pause)
            else:
                class Param:
                    name = self.msg.get(ctx, 'args.query', 'query')
                raise commands.MissingRequiredArgument(Param)

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # SoundCloud searching is possible by prefixing 'scsearch:' instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        async with ctx.channel.typing():
            results = await player.node.get_tracks(query)

        if not results or not results['tracks']:
            return await ctx.send(self.msg.get(ctx, 'music.errors.not_found', '{error} No results found.'))

        embed = discord.Embed(colour=self.config.embeds_color)
        embed.set_footer(text='Requested by ' + str(ctx.author), icon_url=ctx.author.avatar_url)

        def add_track(track):
            embed.title = self.msg.get(ctx, 'music.play.title.single', '{success} Added to the queue!')
            embed.add_field(name=self.msg.get(ctx, 'music.play.song_title', 'Title:'), value='[{0}]({1})'.format(track['info']['title'], track['info']['uri']), inline=False)
            embed.add_field(name=self.msg.get(ctx, 'music.play.uploader','Uploaded by:'), value=track['info']['author'], inline=True)
            embed.add_field(name=self.msg.get(ctx, 'music.play.duration', 'Duration:'), value=self.parse_time(track['info']['length']) if not track['info']['isStream'] else self.msg.get(ctx, 'music.play.live', ':red_circle: **LIVE**'), inline=True)

            if track['info']['position'] > 0:
                embed.add_field(name=self.msg.get(ctx, 'music.play.position', 'Queue position:'), value=track['info']['position'], inline=True)

            track = lavalink.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            if results['playlistInfo']['selectedTrack'] <= 0:
                total_duration = 0
                for track in tracks:
                    total_duration += track['info']['length']
                    player.add(requester=ctx.author.id, track=track)

                embed.title = self.msg.get(ctx, 'music.play.title.multi', '{success} Playlist added to the queue!')
                embed.add_field(name=self.msg.get(ctx, 'music.play.song_title', 'Title:'), value=results['playlistInfo']['name'], inline=False)
                embed.add_field(name=self.msg.get(ctx, 'music.play.playlist.entries', 'Entries:'), value=len(tracks), inline=True)
                embed.add_field(name=self.msg.get(ctx, 'music.play.playlist.total_duration', 'Total duration:'), value=self.parse_time(total_duration), inline=True)
            else:
                add_track(tracks[results['playlistInfo']['selectedTrack']])
        else:
            add_track(results['tracks'][0])

        await ctx.send(embed=embed)
        if not player.is_playing:
            await player.play()

    @commands.command(name='playing', aliases=['np'])
    @commands.check(is_playing)
    async def cmd_playing(self, ctx):
        """
        Shows the track that is currently playing.
        """
        player = self.get_player(ctx.guild.id)
        
        embed = discord.Embed(colour=self.config.embeds_color)
        
        track = player.current
        embed.title = self.msg.get(ctx, 'music.playing.title', ':arrow_forward: Now playing:')
        embed.description = '[{0}]({1}) | `{2}`'.format(track['title'], track['uri'], self.parse_time(track['duration']))

        # print(player.position)
        # print(player.position_timestamp)

        await ctx.send(embed=embed)

    @commands.command(name='skip', aliases=['next'])
    @commands.check(is_playing)
    async def cmd_skip(self, ctx):
        """
        Starts counting votes for skipping the current track.

        If you have requested the current song, you can immediately skip without voting.
        """
        player = self.get_player(ctx.guild.id)
        skip_votes = player.fetch('skip_votes', [])

        if ctx.author.id in skip_votes:
            return await ctx.send(self.msg.get(ctx, 'music.skip.already_voted', '{error} You have already voted to skip this song.'))
        else:
            skip_votes.append(ctx.author.id)
            player.store('skip_votes', skip_votes)
            
            skip_votes = player.fetch('skip_votes', [])
            if len(skip_votes) >= 2 or player.current['requester'] == ctx.author.id or ctx.author.guild_permissions.administrator:
                player.delete('skip_votes')

                await player.skip()
                await ctx.message.add_reaction('⏭️')
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'music.skip.vote_added', '{success} Skip vote added! Currently at **{votes}/3**.'), votes=len(skip_votes)))
    
    @commands.command(name='seek')
    @commands.check(is_playing)
    async def cmd_seek(self, ctx):
        """
        Goes to a specific point in the track.
        """
        player = self.get_player(ctx.guild.id)

        if not player.current['is_seekable']:
            await ctx.send(self.msg.get(ctx, 'music.seek.not_seekable', '{error} You cannot seek this track!'))

    @commands.command(name='queue', aliases=['q'])
    @commands.check(is_playing)
    async def cmd_queue(self, ctx):
        """
        Shows the queue.
        """
        player = self.get_player(ctx.guild.id)

        if len(player.queue) <= 0:
            return await ctx.send(self.msg.get(ctx, 'music.queue.empty', '{error} The queue is empty!'))

        e = discord.Embed(colour=self.config.embeds_color, title=self.msg.format(self.msg.get(ctx, 'music.queue.title', 'Queue for {guild_name}:'), guild_name=ctx.guild.name))
        e.add_field(name=self.msg.get(ctx, 'music.queue.now_playing.title', 'Now playing:'), value=self.msg.format(self.msg.get(ctx, 'music.queue.now_playing.entry',
                    '{repeating} [{track_name}]({track_url}) | `{track_duration}` - Requested by {requester}'), repeating=':repeat: ' if player.repeat else '', track_name=player.current['title'], track_url=player.current['uri'], track_duration=self.parse_time(player.current["duration"]), requester=self.bot.get_user(player.current["requester"]).mention))

        entries = []
        for index, track in enumerate(player.queue):
            entries.append(self.msg.format(self.msg.get(ctx, 'music.queue.entry', '`{index}.` [{track_name}]({track_url}) | `{track_duration}` - Requested by {requester}'), index=index + 1, track_name=track['title'], track_url=track['uri'], track_duration=self.parse_time(track['duration']), requester=self.bot.get_user(track["requester"]).mention))
            
        await menus.MenuPages(source=EmbedDescriptionPaginator(ctx, e, entries, per_page=10), clear_reactions_after=True).start(ctx)

    @commands.group(name='remove', aliases=['rm'], invoke_without_command=True)
    @commands.check(is_playing)
    async def cmd_remove(self, ctx, index : int):
        """
        Removes a song from the queue.
        """
        if ctx.invoked_subcommand is None:
            player = self.get_player(ctx.guild.id)

            if len(player.queue) <= 0:
                return await ctx.send(self.msg.get(ctx, 'music.queue.empty', '{error} The queue is empty!'))

            if index > len(player.queue) or index <= 0:
                return await ctx.send(self.msg.get(ctx, 'music.remove.not_exist', '{error} The track was not found in the queue!'))
            
            to_remove = player.queue[index - 1]

            if to_remove['requester'] == ctx.author.id or ctx.author.guild_permissions.administrator:
                player.queue.remove(to_remove)
                await ctx.send(self.msg.format(self.msg.get(ctx, 'music.remove.removed', '{success} Removed `{removed}` from the queue.'), removed=to_remove['title']))
            else:
                await ctx.send(self.msg.get(ctx, 'music.remove.cannot_remove_other', '{error} You can remove only songs requested by you.'))

    @cmd_remove.command(name='all')
    @commands.check(is_playing)
    async def cmd_remove_all(self, ctx):
        """
        Removes all the songs in the queue.
        """
        player = self.get_player(ctx.guild.id)

        if all(track['requester'] == ctx.author.id for track in player.queue) or ctx.author.guild_permissions.administrator:
            player.queue.clear()
            await ctx.send(self.msg.get(ctx, 'music.remove.all.removed', '{success} Removed all entries.'))
        else:
            await ctx.send(self.msg.get(ctx, 'music.remove.all.cannot_remove_other', '{error} You can remove all the entries only if them are all requested by you.'))
    
    @commands.command(name='repeat', aliases=['loop'])
    @commands.check(is_playing)
    async def cmd_repeat(self, ctx):
        """
        Toggles the repeat of the current track. 
        """
        player = self.get_player(ctx.guild.id)
        player.repeat = not player.repeat

        if player.repeat:
            await ctx.send(self.msg.get(ctx, 'music.repeat.enabled', ':repeat: **Track repeat enabled!**'))
        else:
            await ctx.send(self.msg.get(ctx, 'music.repeat.disabled', ':arrow_forward: **Track repeat disabled!**'))

    @commands.command(name='shuffle')
    @commands.check(is_playing)
    async def cmd_shuffle(self, ctx):
        """
        Shuffles the queue.
        """
        player = self.get_player(ctx.guild.id)
        player.shuffle = not player.shuffle

        if player.shuffle:
            await ctx.send(self.msg.get(ctx, 'music.shuffle.enabled', ':twisted_rightwards_arrows: **Queue shuffling enabled!**'))
        else:
            await ctx.send(self.msg.get(ctx, 'music.shuffle.disabled', ':arrow_forward: **Queue shuffling disabled!**'))

    @commands.command(name='pause')
    @commands.check(is_playing)
    async def cmd_pause(self, ctx):
        """
        Pause/Resume the playback.
        """
        player = self.get_player(ctx.guild.id)

        await player.set_pause(not player.paused)

        if player.paused:
            await ctx.message.add_reaction('⏸️')
        else:
            await ctx.message.add_reaction('▶️')
    
    @commands.command(name='volume', aliases=['vol'])
    @commands.check(is_playing)
    async def cmd_volume(self, ctx, *, volume: int = None):
        """
        Allows you to view, raise or lower the volume.
        """
        player = self.get_player(ctx.guild.id)

        current_volume = player.volume

        if volume is None:
            if current_volume < 50:
                string = self.msg.get(ctx, 'music.volume.current.low',
                                 '🔉 Current volume is **{volume}%**.')
            else:
                string = self.msg.get(ctx, 'music.volume.current.high',
                                 '🔊 Current volume is **{volume}%**.')
            return await ctx.send(self.msg.format(string, volume=current_volume))

        if volume == player.volume:
            return await ctx.send(self.msg.format(self.msg.get(ctx, 'music.volume.same', '{error} Volume is already set to **{volume}%**.'), volume=volume))

        if ctx.author.guild_permissions.administrator:
            if volume > 100 or volume < 1:
                return await ctx.send(self.msg.get(ctx, 'music.volume.not_valid', '{error} Volume must be between **1** and **100**!'))

            await player.set_volume(volume)

            if current_volume < volume:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'music.volume.raised', '{success} Volume raised to **{level}%**.'), level=volume))
            else:
                await ctx.send(self.msg.format(self.msg.get(ctx, 'music.volume.down', '{success} Volume down to **{level}%**.'), level=volume))
        else:
            raise commands.MissingPermissions(['administrator'])

    @commands.command(name='stop', aliases=['dc', 'disconnect', 'leave'])
    @commands.check(is_playing)
    async def cmd_stop(self, ctx):
        """
        Stops the playback and clears the queue.
        """
        player = self.get_player(ctx.guild.id)

        player.delete('skip_votes')
        player.queue.clear()
        await player.stop()

        await ctx.guild.change_voice_state(channel=None)
        await ctx.message.add_reaction('⏹')


def setup(bot):
    bot.add_cog(Music(bot))
