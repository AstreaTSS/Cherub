import importlib
import io
import typing

import naff
import tansy
from PIL import Image

import common.emoji_utils as emoji_utils
import common.utils as utils


class UploadEmoji(utils.Extension):
    def __init__(self, bot: utils.CherubBase):
        self.bot = bot
        self.name = "Upload Emoji"

    @tansy.slash_command(
        name="add-emoji",
        description="Adds the URL, emoji, or image given as an emoji to this server.",
        default_member_permissions=naff.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    @utils.bot_can_upload_emoji()
    async def add_emoji(
        self,
        ctx: utils.GuildInteractionContext,
        emoji: typing.Optional[str] = tansy.Option(
            "The emoji or image URL to upload.", default=None
        ),
        attachment: typing.Optional[naff.Attachment] = tansy.Option(
            "The file to use as an emoji.", default=None
        ),
        name: typing.Optional[str] = tansy.Option(
            "The name to use for the emoji.", default=None
        ),
    ):
        if not emoji and not attachment:
            raise naff.errors.BadArgument(
                "Either an emoji, URL, or an attachment must be provided."
            )
        if emoji and attachment:
            raise naff.errors.BadArgument(
                "Only one of `emoji` or `attachment` can be provided."
            )

        await ctx.defer()

        emoji_id = None
        emoji_url = None
        emoji_ext = None
        emoji_name = name

        if emoji:
            try:
                if isinstance(emoji, naff.PartialEmoji):
                    # happens with commands using the direct callback
                    partial_emoji = emoji
                else:
                    partial_emoji = (
                        await emoji_utils.CustomPartialEmojiConverter.convert(
                            ctx, emoji
                        )
                    )

                emoji_id = int(partial_emoji.id)  # type: ignore
                emoji_url = emoji_utils.get_emoji_url(partial_emoji)
                emoji_ext = "gif" if partial_emoji.animated else "png"
                emoji_name = emoji_name or partial_emoji.name

            except naff.errors.BadArgument:
                emoji_url, emoji_ext = await emoji_utils.get_image_url(emoji)
                if not emoji_url or not emoji_ext:
                    raise naff.errors.BadArgument(
                        "This argument is not a valid emoji or image URL."
                    ) from None
                emoji_name = (
                    emoji_name or emoji_url.split("/")[-1].split(".", maxsplit=1)[0]
                )

        elif attachment:
            emoji_url = attachment.url

            if not attachment.content_type:
                raise naff.errors.BadArgument("The attachment is not a valid image.")

            emoji_ext = attachment.content_type.split("/")[1]
            if emoji_ext not in emoji_utils.IMAGE_EXTS:
                raise naff.errors.BadArgument("The attachment is not a valid image.")

            emoji_name = emoji_name or attachment.filename

        if not emoji_url or not emoji_name or not emoji_ext:
            # no idea how this would happen
            raise naff.errors.BadArgument("Invalid argument passed.")

        guild_emojis = await ctx.guild.fetch_all_custom_emojis()

        if emoji_id:
            if next((e for e in guild_emojis if e.id and int(e.id) == emoji_id), None):
                raise utils.CustomCheckFailure("This emoji is already on this server.")

        elif next((e for e in guild_emojis if e.name == emoji_name), None):
            raise utils.CustomCheckFailure(
                f"There is already an emoji named `{emoji_name}`."
            )

        animated = False
        #  256 KiB, which i assume discord uses
        raw_data = await emoji_utils.get_file_with_limit(emoji_url, 262144)
        emoji_data = io.BytesIO(raw_data)

        if emoji_ext == "gif":
            # you see, gifs can be animated or not animated
            # so we need to check for that via an admittedly risky operation

            emoji_image = None

            try:
                # i think this operation is basic enough not to need a generator?
                # not totally sure, though
                emoji_image = Image.open(emoji_data)
                animated = emoji_image.is_animated
            except:
                if emoji_image:
                    emoji_image.close()
                raise naff.errors.BadArgument("Invalid GIF provided.")
            else:
                emoji_data.seek(0)

        if animated:
            emoji_count = len(tuple(e for e in guild_emojis if e.animated))
        else:
            emoji_count = len(tuple(e for e in guild_emojis if not e.animated))

        if emoji_count >= ctx.guild.emoji_limit:
            raise utils.CustomCheckFailure(
                "This guild has no more emoji slots for that type of emoji."
            )

        try:
            uploaded_emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name,
                imagefile=emoji_data,
                reason=f"Created by {str(ctx.author)}.",
            )
        except naff.errors.HTTPException as e:
            raise utils.CustomCheckFailure(
                "".join(
                    (
                        (
                            "I was unable to add this emoji. This might be due to me"
                            " not having the "
                        ),
                        (
                            "permissions or the name being improper in some way. Maybe"
                            " this error will help you.\n\n"
                        ),
                        f"Error: `{e}`",
                    )
                )
            ) from None
        finally:
            emoji_data.close()

        await ctx.send(f"Added {str(uploaded_emoji)}!")

    @tansy.slash_command(
        name="clone-emoji",
        description="Clones an emoji from one server to this one.",
        default_member_permissions=naff.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    @utils.bot_can_upload_emoji()
    async def clone_emoji(
        self,
        ctx: utils.GuildInteractionContext,
        emoji: naff.PartialEmoji = tansy.Option(
            "The emoji to clone.",
            type=str,
            converter=emoji_utils.CustomPartialEmojiConverter,
        ),
    ):
        await self.add_emoji.call_with_binding(
            self.add_emoji.callback, ctx, emoji=emoji, attachment=None, name=None
        )

    @naff.context_menu(
        "Add First Emoji",
        naff.CommandTypes.MESSAGE,
        default_member_permissions=naff.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )  # type: ignore
    async def add_first_emoji(self, ctx: utils.GuildInteractionContext):
        message: naff.Message = ctx.target  # type: ignore

        if match := emoji_utils.DISCORD_EMOJI_REGEX.search(message.content):
            emoji_animated = bool(match[1])
            emoji_name = match[2]
            emoji_id = int(match[3])
            emoji = naff.PartialEmoji(
                id=emoji_id, name=emoji_name, animated=emoji_animated
            )
            await self.add_emoji.call_with_binding(
                self.add_emoji.callback, ctx, emoji=emoji, attachment=None, name=None
            )
        else:
            raise naff.errors.BadArgument("No emojis found in this message.")


def setup(bot):
    importlib.reload(utils)
    importlib.reload(emoji_utils)
    UploadEmoji(bot)
