import importlib
import re

import naff
import tansy

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
        emoji: naff.PartialEmoji = tansy.Option(
            "The emoji to get the URL of.",
            type=str,
            converter=emoji_utils.CustomPartialEmojiConverter,
        ),
    ):
        await ctx.send(f"URL: {emoji_utils.get_emoji_url(emoji)}", ephemeral=True)

    @naff.context_menu("Get Emoji URLs", naff.CommandTypes.MESSAGE)  # type: ignore
    async def get_emoji_urls(self, ctx: utils.CherubInteractionContext) -> None:
        await ctx.defer(ephemeral=True)

        message: naff.Message = ctx.target  # type: ignore

        if matches := emoji_utils.DISCORD_EMOJI_REGEX.findall(message.content):
            emoji_urls: list[str] = []

            for match in matches:
                emoji_animated = bool(match[0])
                emoji_name = match[1]
                emoji_id = int(match[2])
                emoji = naff.PartialEmoji(
                    id=emoji_id, name=emoji_name, animated=emoji_animated
                )

                emoji_urls.append(emoji_utils.get_emoji_url(emoji))

            # removes dups while preserving order
            emoji_urls_str = "\n".join(dict.fromkeys(emoji_urls))
            await ctx.send(f"URL(s):\n{emoji_urls_str}", ephemeral=True)
        else:
            raise naff.errors.BadArgument("No emojis found in this message.")


def setup(bot):
    importlib.reload(utils)
    importlib.reload(emoji_utils)
    GetEmojis(bot)
