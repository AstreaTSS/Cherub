import asyncio
import importlib
import io
import typing

import interactions as ipy
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
        default_member_permissions=ipy.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    @utils.bot_can_upload_emoji()
    async def add_emoji(
        self,
        ctx: utils.GuildInteractionContext,
        emoji: typing.Optional[str] = tansy.Option(
            "The emoji or image URL to upload.", default=None
        ),
        attachment: typing.Optional[ipy.Attachment] = tansy.Option(
            "The file to use as an emoji.", default=None
        ),
        name: typing.Optional[str] = tansy.Option(
            "The name to use for the emoji.", default=None
        ),
    ):
        if not emoji and not attachment:
            raise ipy.errors.BadArgument(
                "Either an emoji, URL, or an attachment must be provided."
            )
        if emoji and attachment:
            raise ipy.errors.BadArgument(
                "Only one of `emoji` or `attachment` can be provided."
            )

        emoji_id = None
        emoji_url = None
        emoji_ext = None
        emoji_name = name

        if emoji:
            try:
                if isinstance(emoji, ipy.PartialEmoji):
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

            except ipy.errors.BadArgument:
                emoji_url, emoji_ext = await emoji_utils.get_image_url(emoji)
                if not emoji_url or not emoji_ext:
                    raise ipy.errors.BadArgument(
                        "This argument is not a valid emoji or image URL."
                    ) from None
                emoji_name = (
                    emoji_name or emoji_url.split("/")[-1].split(".", maxsplit=1)[0]
                )

        elif attachment:
            emoji_url = attachment.url

            if not attachment.content_type:
                raise ipy.errors.BadArgument("The attachment is not a valid image.")

            emoji_ext = attachment.content_type.split("/")[1]
            if emoji_ext not in emoji_utils.IMAGE_EXTS:
                raise ipy.errors.BadArgument("The attachment is not a valid image.")

            emoji_name = emoji_name or attachment.filename

        if not emoji_url or not emoji_name or not emoji_ext:
            # no idea how this would happen
            raise ipy.errors.BadArgument("Invalid argument passed.")

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
                raise ipy.errors.BadArgument("Invalid GIF provided.")
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
        except ipy.errors.HTTPException as e:
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
        default_member_permissions=ipy.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    @utils.bot_can_upload_emoji()
    async def clone_emoji(
        self,
        ctx: utils.GuildInteractionContext,
        emoji: ipy.PartialEmoji = tansy.Option(
            "The emoji to clone.",
            type=str,
            converter=emoji_utils.CustomPartialEmojiConverter,
        ),
    ):
        await self.add_emoji.call_with_binding(
            self.add_emoji.callback, ctx, emoji=emoji, attachment=None, name=None
        )

    @ipy.context_menu(
        "Add First Emoji",
        context_type=ipy.CommandType.MESSAGE,
        default_member_permissions=ipy.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    async def add_first_emoji(self, ctx: utils.GuildInteractionContext):
        message: ipy.Message = ctx.target  # type: ignore

        if match := emoji_utils.DISCORD_EMOJI_REGEX.search(message.content):
            emoji_animated = bool(match[1])
            emoji_name = match[2]
            emoji_id = int(match[3])
            emoji = ipy.PartialEmoji(
                id=emoji_id, name=emoji_name, animated=emoji_animated
            )
            await self.add_emoji.call_with_binding(
                self.add_emoji.callback, ctx, emoji=emoji, attachment=None, name=None
            )
        else:
            raise ipy.errors.BadArgument("No emojis found in this message.")

    @ipy.context_menu(
        "Add Emojis",
        context_type=ipy.CommandType.MESSAGE,
        default_member_permissions=ipy.Permissions.MANAGE_EMOJIS_AND_STICKERS,
        dm_permission=False,
    )
    @utils.bot_can_upload_emoji()
    @ipy.auto_defer(ephemeral=True)
    async def add_emojis_from_message(self, ctx: utils.GuildInteractionContext):
        message: ipy.Message = ctx.target  # type: ignore

        if not (matches := emoji_utils.DISCORD_EMOJI_REGEX.findall(message.content)):
            raise ipy.errors.BadArgument("No emojis found in this message.")

        guild_emojis = await ctx.guild.fetch_all_custom_emojis()
        guild_emoji_ids = frozenset({int(e.id) for e in guild_emojis if e.id})

        emoji_options: list[ipy.StringSelectOption] = []
        emoji_ids: set[int] = set()

        for match in matches:
            emoji_name = match[1]
            emoji_id = int(match[2])
            emoji = ipy.PartialEmoji(
                id=emoji_id, name=emoji_name, animated=bool(match[0])
            )

            if emoji_id in guild_emoji_ids:
                continue

            if emoji_id in emoji_ids:
                continue
            emoji_ids.add(emoji_id)

            emoji_options.append(
                ipy.StringSelectOption(
                    label=emoji_name,
                    value=f"{emoji_name}|{emoji_utils.get_emoji_url(emoji)}",
                    emoji=emoji,
                )
            )

        if not emoji_options:
            raise ipy.errors.BadArgument(
                "No emojis found in this message that aren't already in this server."
            )

        if len(emoji_options) > 25:
            emoji_options = emoji_options[:25]

        emoji_menu = ipy.StringSelectMenu(
            *emoji_options,
            placeholder="Select Emojis",
            max_values=len(emoji_options),
        )

        msg = await ctx.send(
            "Select the emojis you want to add.", components=[emoji_menu]
        )

        try:
            menu_event = await self.bot.wait_for_component(
                components=[emoji_menu], timeout=60
            )

            emoji_menu.disabled = True
            await ctx.edit(
                msg,
                content="Select the emojis you want to add.",
                components=[emoji_menu],
            )
            await menu_event.ctx.defer(ephemeral=True)

            new_animated_emojis_size = 0
            new_static_emojis_size = 0

            animated_emoji_count = len(tuple(e for e in guild_emojis if e.animated))
            normal_emoji_count = len(tuple(e for e in guild_emojis if not e.animated))

            for emoji_entry in menu_event.ctx.values:
                if emoji_entry.endswith(".gif"):
                    new_animated_emojis_size += 1
                else:
                    new_static_emojis_size += 1

            if animated_emoji_count + new_animated_emojis_size > ctx.guild.emoji_limit:
                raise ipy.errors.BadArgument(
                    "This guild has no more emoji slots for animated emojis."
                )

            if normal_emoji_count + new_static_emojis_size > ctx.guild.emoji_limit:
                raise ipy.errors.BadArgument(
                    "This guild has no more emoji slots for static emojis."
                )

            uploaded_emojis: list[ipy.CustomEmoji] = []

            for emoji_entry in menu_event.ctx.values:
                emoji_split = emoji_entry.split("|")
                emoji_url = emoji_split[1]
                emoji_data_bytes = await emoji_utils.get_file_with_limit(
                    emoji_url, 262144
                )
                emoji_data = io.BytesIO(emoji_data_bytes)

                try:
                    uploaded_emoji = await ctx.guild.create_custom_emoji(
                        name=emoji_split[0],
                        imagefile=emoji_data,
                        reason=f"Created by {str(ctx.author)}.",
                    )
                    uploaded_emojis.append(uploaded_emoji)
                except ipy.errors.HTTPException as e:
                    raise utils.CustomCheckFailure(
                        "".join(
                            (
                                (
                                    f"I was unable to add {emoji_split[0]}. This might"
                                    " be due to me not having the "
                                ),
                                (
                                    "permissions or the name being improper in some"
                                    " way. Maybe this error will help you.\n\n"
                                ),
                                f"Error: `{e}`",
                            )
                        )
                    ) from None
                finally:
                    emoji_data.close()

            emoji_list = ", ".join(str(e) for e in uploaded_emojis)

            if not ipy.Timestamp.utcnow() > menu_event.ctx.expires_at:
                await menu_event.ctx.send(
                    content=f"Successfully added emojis: {emoji_list}", ephemeral=True
                )
            else:
                await ctx.channel.send(
                    content=(
                        f"{ctx.author.mention}, successfully added emojis: {emoji_list}"
                    ),
                    delete_after=10,
                )

        except asyncio.TimeoutError:
            await ctx.edit(
                msg,
                content="You took too long to select emojis. Please try again.",
                components=[],
            )
            return


def setup(bot):
    importlib.reload(utils)
    importlib.reload(emoji_utils)
    UploadEmoji(bot)
