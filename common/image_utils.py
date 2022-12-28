import naff


class WrappedPartialEmojiConverter(naff.PartialEmojiConverter):
    async def convert(self, ctx: naff.Context, argument: str) -> naff.PartialEmoji:
        try:
            return await super().convert(ctx, argument)
        except naff.errors.BadArgument as e:
            raise naff.errors.BadArgument(
                str(e).replace("PartialEmoji", "a Discord emoji")
            ) from None


def get_emoji_url(emoji: naff.PartialEmoji):
    fmt = "gif" if emoji.animated else "png"
    return f"{naff.Asset.BASE}/emojis/{emoji.id}.{fmt}"
