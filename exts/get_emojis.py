import importlib
import re

import naff
import tansy

import common.image_utils as image_utils
import common.utils as utils

DISCORD_EMOJI_REGEX = re.compile(r"<(a?):([a-zA-Z0-9\_]{1,32}):([0-9]{15,20})>")


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
            converter=image_utils.WrappedPartialEmojiConverter,
        ),
    ):
        await ctx.send(f"URL: {image_utils.get_emoji_url(emoji)}", ephemeral=True)

    @naff.context_menu("Get Emoji URLs", naff.CommandTypes.MESSAGE)  # type: ignore
    async def get_emoji_urls(self, ctx: utils.CherubInteractionContext) -> None:
        await ctx.defer(ephemeral=True)

        message: naff.Message = ctx.target  # type: ignore

        if matches := DISCORD_EMOJI_REGEX.findall(message.content):
            emoji_urls: list[str] = []

            for match in matches:
                emoji_animated = bool(match.group(1))
                emoji_name = match.group(2)
                emoji_id = int(match.group(3))
                emoji = naff.PartialEmoji(
                    id=emoji_id, name=emoji_name, animated=emoji_animated
                )

                emoji_urls.append(image_utils.get_emoji_url(emoji))

            # removes dups while preserving order
            emoji_urls_str = "\n".join(dict.fromkeys(emoji_urls))
            await ctx.send(f"URL(s):\n{emoji_urls_str}", ephemeral=True)
        else:
            raise naff.errors.BadArgument("No emojis found in this message.")


def setup(bot):
    importlib.reload(utils)
    importlib.reload(image_utils)
    GetEmojis(bot)
