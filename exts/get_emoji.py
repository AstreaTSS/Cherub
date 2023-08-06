import importlib

import interactions as ipy
import tansy
from interactions.models.internal.application_commands import auto_defer

import common.emoji_utils as emoji_utils
import common.utils as utils


class GetEmojis(utils.Extension):
    def __init__(self, bot: utils.CherubBase) -> None:
        self.bot = bot
        self.name = "Get Emoji"

    @tansy.slash_command(
        name="emoji-url", description="Get the URL of a Discord emoji."
    )
    async def emoji_url(
        self,
        ctx: utils.CherubInteractionContext,
        emoji: ipy.PartialEmoji = tansy.Option(
            "The emoji to get the URL of.",
            type=str,
            converter=emoji_utils.CustomPartialEmojiConverter,
        ),
    ):
        await ctx.send(f"URL: {emoji_utils.get_emoji_url(emoji)}", ephemeral=True)

    @ipy.context_menu("Get Emoji URLs", context_type=ipy.CommandType.MESSAGE)
    @auto_defer(enabled=True, ephemeral=True)
    async def get_emoji_urls(self, ctx: utils.CherubInteractionContext) -> None:
        message: ipy.Message = ctx.target  # type: ignore

        if not (matches := emoji_utils.DISCORD_EMOJI_REGEX.findall(message.content)):
            raise ipy.errors.BadArgument("No emojis found in this message.")

        emoji_urls: list[str] = []
        for match in matches:
            emoji_name = match[1]
            emoji_id = int(match[2])
            emoji = ipy.PartialEmoji(
                id=emoji_id, name=emoji_name, animated=bool(match[0])
            )

            emoji_urls.append(emoji_utils.get_emoji_url(emoji))

        # removes dups while preserving order
        emoji_urls_str = "\n".join(dict.fromkeys(emoji_urls))
        await ctx.send(f"URL(s):\n{emoji_urls_str}", ephemeral=True)


def setup(bot):
    importlib.reload(utils)
    importlib.reload(emoji_utils)
    GetEmojis(bot)
