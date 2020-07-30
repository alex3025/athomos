from discord.ext import menus

from utils.messages import Messages


class EmbedPaginator(menus.ListPageSource):
    def __init__(self, embed, fields, ctx, per_page=2):
        self.msg = Messages()
        self.ctx = ctx
        self.embed = embed

        super().__init__(fields, per_page=per_page)

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.set_footer(text=self.msg.format(self.msg.get(self.ctx, 'paginator.pages', 'Page {current_page}/{all_pages}'), current_page=menu.current_page + 1, all_pages=self.get_max_pages() if not self.get_max_pages() <= 0 else '1'))
        offset = menu.current_page * self.per_page
        for _, fields in enumerate(entries, start=offset):
            for name, value in fields.items():
                self.embed.add_field(name=name, value=value[:64] + '...' if len(value) > 64 else value, inline=False)
        return self.embed
