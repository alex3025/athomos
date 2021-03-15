import json
from discord.ext import commands

from .logger import Logger
from .database import Database


log = Logger()
log.info('Loaded i18n data!')

db = Database().db


class Messages:
    def placeholders(self, message):
        class format_dict(dict):
            def __missing__(key):
                return '{%s}' % key

        placeholders = {
            'JoinedAtDate': message.author.joined_at.strftime('%d/%m/%Y'),
            'JoinedAtTime': message.author.joined_at.strftime('%H:%M'),
            'Mention': message.author.mention,
            'Username': message.author.name,
            'ServerMembersCount': len(message.author.guild.members)
        }

        return format_dict(placeholders)

    def parse(self, file):
        try:
            with open(file, encoding='utf-8') as data:
                try:
                    parsed = json.load(data)
                except Exception:
                    log.error('Error parsing {0} as JSON'.format(file), exc_info=True)
                    parsed = {}
        except FileNotFoundError:
            parsed = {}
        return parsed

    def format(self, string, **placeholders):
        class format_dict(dict):
            def __missing__(self, key):
                return '{%s}' % key

        return string.format_map(format_dict(placeholders))

    def get_locale(self, guildID: int):
        return db.find_one({'id': guildID})['language'], guildID

    def get(self, locale_ctx, index, fallback=None):
        if isinstance(locale_ctx, commands.Context):
            (locale, guild_id) = self.get_locale(locale_ctx.guild.id)
        else:
            locale, guild_id = locale_ctx, None

        try:
            data = self.parse(f'config/i18n/{locale}.json')
            for category in index.split('.'):
                data = data[category]

        except (KeyError, FileNotFoundError):
            log.warning(f'Could not grab data from i18n key: {index}')
            data = fallback

        return self.format(data, success='<:athomos_success:600278477421281280>', error='<:athomos_error:600278499055370240>', prefix=db.find_one({'id': guild_id})['prefix'] if guild_id else '!')
