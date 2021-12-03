from discord.ext import menus

from utils.messages import Messages


def pageCount(msg, ctx, menu, maxPages=0):
    return msg.format(msg.get(ctx, 'paginator.pages', 'Page {current_page} of {all_pages}'), current_page=menu.current_page + 1, all_pages=maxPages if not maxPages <= 0 else '1')


class EmbedFieldsPaginator(menus.ListPageSource):
    def __init__(self, embed, fields, ctx, per_page=2):
        self.msg = Messages()
        self.ctx = ctx
        self.embed = embed

        super().__init__(fields, per_page=per_page)

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.set_footer(text=pageCount(self.msg, self.ctx, menu, self.get_max_pages()))
        offset = menu.current_page * self.per_page

        for _, fields in enumerate(entries, start=offset):
            for name, value in fields.items():
                self.embed.add_field(name=name, value=value[:64] + '...' if len(value) > 64 else value, inline=False)

        return self.embed


class EmbedDescriptionPaginator(menus.ListPageSource):
    def __init__(self, ctx, embed, entries, per_page=2):
        self.ctx = ctx
        self.embed = embed

        self.msg = Messages()

        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        self.embed.set_footer(text=pageCount(self.msg, self.ctx, menu, self.get_max_pages()))

        self.embed.description = '\n'.join(f'{text}' for _, text in enumerate(entries, start=offset))

        return self.embed
