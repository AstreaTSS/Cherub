import collections
import logging
import os
import traceback
import typing
from pathlib import Path

import aiohttp
import interactions as ipy
from interactions.ext import prefixed_commands as prefixed

import common.models as models


if typing.TYPE_CHECKING:
    import asyncio

    class CherubBase(prefixed.PrefixedInjectedClient):
        init_load: bool
        fully_ready: asyncio.Event
        color: ipy.Color
        owner: ipy.User

else:

    class CherubBase(ipy.Client):
        pass


class CherubContextMixin:
    bot: CherubBase
    guild: ipy.Guild
    guild_id: ipy.Snowflake


class GuildContextMixin(CherubContextMixin):
    guild: ipy.Guild
    guild_id: ipy.Snowflake


class CherubContext(CherubContextMixin, ipy.BaseContext):
    pass


class CherubInteractionContext(CherubContextMixin, ipy.InteractionContext):
    pass


class CherubSlashContext(CherubContextMixin, ipy.SlashContext):
    pass


class GuildInteractionContext(GuildContextMixin, ipy.InteractionContext):
    pass


def error_embed_generate(error_msg: str):
    return ipy.Embed(color=ipy.RoleColors.RED, description=error_msg)


async def error_handle(
    bot: CherubBase,
    error: Exception,
    ctx: typing.Optional[ipy.BaseContext] = None,
):
    # handles errors and sends them to owner
    if isinstance(error, aiohttp.ServerDisconnectedError):
        to_send = "Disconnected from server!"
    else:
        error_str = error_format(error)
        logging.getLogger("cherub").error(error_str)

        chunks = line_split(error_str, split_by=40)
        for i in range(len(chunks)):
            chunks[i][0] = f"```py\n{chunks[i][0]}"
            chunks[i][-1] += "\n```"

        final_chunks: list[str | ipy.Embed] = [
            error_embed_generate("\n".join(chunk)) for chunk in chunks
        ]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks

    await msg_to_owner(bot, to_send)

    if ctx:
        if isinstance(ctx, prefixed.PrefixedContext):
            await ctx.reply(
                "An internal error has occured. The bot owner has been notified."
            )
        elif isinstance(ctx, ipy.InteractionContext):
            await ctx.send(
                content=(
                    "An internal error has occured. The bot owner has been notified."
                ),
                ephemeral=True,
            )


def error_format(error: Exception):
    # simple function that formats an exception
    return "".join(traceback.format_exception(error))


def string_split(string: str):
    # simple function that splits a string into 1950-character parts
    return [string[i : i + 1950] for i in range(0, len(string), 1950)]


async def msg_to_owner(
    bot: CherubBase,
    chunks: list[str] | list[ipy.Embed] | list[str | ipy.Embed] | str | ipy.Embed,
):
    if not isinstance(chunks, list):
        chunks = [chunks]

    # sends a message to the owner
    for chunk in chunks:
        if isinstance(chunk, ipy.Embed):
            await bot.owner.send(embeds=chunk)
        else:
            await bot.owner.send(chunk)


def line_split(content: str, split_by=20):
    content_split = content.splitlines()
    return [
        content_split[x : x + split_by] for x in range(0, len(content_split), split_by)
    ]


def file_to_ext(str_path, base_path):
    # changes a file to an import-like string
    str_path = str_path.replace(base_path, "")
    str_path = str_path.replace("/", ".")
    return str_path.replace(".py", "")


def get_all_extensions(str_path, folder="exts"):
    # gets all extensions in a folder
    ext_files = collections.deque()
    loc_split = str_path.split(folder)
    base_path = loc_split[0]

    if base_path == str_path:
        base_path = base_path.replace("main.py", "")
    base_path = base_path.replace("\\", "/")

    if base_path[-1] != "/":
        base_path += "/"

    pathlist = Path(f"{base_path}/{folder}").glob("**/*.py")
    for path in pathlist:
        str_path = str(path.as_posix())
        str_path = file_to_ext(str_path, base_path)

        ext_files.append(str_path)

    return ext_files


_bot_color = ipy.Color(int(os.environ["BOT_COLOR"]))


def make_embed(description: str, *, title: str | None = None) -> ipy.Embed:
    return ipy.Embed(
        title=title,
        description=description,
        color=_bot_color,
        timestamp=ipy.Timestamp.utcnow(),
    )


async def fetch_config(guild_id: ipy.Snowflake_Type):
    maybe_config = await models.Config.find_one(models.Config.guild_id == str(guild_id))
    if maybe_config is None:
        maybe_config = models.Config(guild_id=str(guild_id), pinboards={})
        await maybe_config.create()
    return maybe_config


class CustomCheckFailure(ipy.errors.BadArgument):
    # custom classs for custom prerequisite failures outside of normal command checks
    pass


def bot_can_upload_emoji() -> typing.Any:
    async def predicate(ctx: GuildInteractionContext):
        bot_perms: ipy.Permissions = ctx.channel.permissions_for(ctx.guild.me)  # type: ignore
        if ipy.Permissions.MANAGE_EMOJIS_AND_STICKERS not in bot_perms:
            raise CustomCheckFailure("The bot can't upload emojis on this server.")

        return True

    return ipy.check(predicate)  # type: ignore


async def _global_checks(ctx: CherubContext):
    return ctx.bot.fully_ready.is_set()


class Extension(ipy.Extension):
    def __new__(cls, bot: CherubBase, *args, **kwargs):
        new_cls = super().__new__(cls, bot, *args, **kwargs)
        new_cls.add_ext_check(_global_checks)  # type: ignore
        return new_cls
