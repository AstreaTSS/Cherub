import collections
import logging
import traceback
import typing
from pathlib import Path

import aiohttp
import naff


def error_embed_generate(error_msg: str):
    return naff.Embed(color=naff.RoleColors.RED, description=error_msg)


async def error_handle(
    bot: naff.Client, error: Exception, ctx: typing.Optional[naff.Context] = None
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

        final_chunks: list[str | naff.Embed] = [
            error_embed_generate("\n".join(chunk)) for chunk in chunks
        ]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks

    await msg_to_owner(bot, to_send)

    if ctx:
        if isinstance(ctx, naff.PrefixedContext):
            await ctx.reply(
                "An internal error has occured. The bot owner has been notified."
            )
        elif isinstance(ctx, naff.InteractionContext):
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
    bot: naff.Client,
    chunks: list[str] | list[naff.Embed] | list[str | naff.Embed] | str | naff.Embed,
):
    if not isinstance(chunks, list):
        chunks = [chunks]

    # sends a message to the owner
    for chunk in chunks:
        if isinstance(chunk, naff.Embed):
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


class CustomCheckFailure(naff.errors.BadArgument):
    # custom classs for custom prerequisite failures outside of normal command checks
    pass


async def _global_checks(ctx: naff.Context):
    return ctx.bot.fully_ready.is_set()


class Extension(naff.Extension):
    def __new__(cls, bot: naff.Client, *args, **kwargs):
        new_cls = super().__new__(cls, bot, *args, **kwargs)
        new_cls.add_ext_check(_global_checks)  # type: ignore
        return new_cls
