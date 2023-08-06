import asyncio
import re
import typing

import aiohttp
import humanize
import interactions as ipy

DISCORD_EMOJI_REGEX = re.compile(r"<(a?):([a-zA-Z0-9\_]{1,32}):([0-9]{15,})>")
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}


async def type_from_url(url: str) -> typing.Optional[str]:
    # gets type of data from url
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            data = await resp.content.read(12)
            tup_data = tuple(data)

            # first 7 bytes of most pngs
            png_list = (0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
            if tup_data[:8] == png_list:
                return "png"

            # fmt: off
            # first 12 bytes of most jp(e)gs. EXIF is a bit wierd, and so some manipulating has to be done
            jfif_list = (0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01)
            # fmt: on
            exif_lists = (
                (0xFF, 0xD8, 0xFF, 0xE1),
                (0x45, 0x78, 0x69, 0x66, 0x00, 0x00),
            )

            if tup_data == jfif_list or (
                tup_data[:4] == exif_lists[0] and tup_data[6:] == exif_lists[1]
            ):
                return "jpg"

            # first 3 bytes of some jp(e)gs.
            if tup_data[:3] == (0xFF, 0xD8, 0xFF):
                return "jpg"

            # copied from d.py's _get_mime_type_for_image
            if tup_data[:3] == b"\xff\xd8\xff" or tup_data[6:10] in (
                b"JFIF",
                b"Exif",
            ):
                return "jpg"

            # first 6 bytes of most gifs. last two can be different, so we have to handle that
            gif_lists = ((0x47, 0x49, 0x46, 0x38), ((0x37, 0x61), (0x39, 0x61)))
            if tup_data[:4] == gif_lists[0] and tup_data[4:6] in gif_lists[1]:
                return "gif"

            # first 12 bytes of most webps. middle four are file size, so we ignore that
            webp_lists = ((0x52, 0x49, 0x46, 0x46), (0x57, 0x45, 0x42, 0x50))
            if tup_data[:4] == webp_lists[0] and tup_data[8:] == webp_lists[1]:
                return "webp"

    return None


async def get_image_url(url: str):
    # handles getting true image url from a url

    try:
        file_type = await type_from_url(url)
    except aiohttp.InvalidURL:
        return (None, None)

    return (url, file_type) if file_type in IMAGE_EXTS else (None, None)


async def get_file_with_limit(url: str, limit: int, *, equal_to: bool = True):
    # gets a file as long as it's under the limit (in bytes)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ipy.errors.BadArgument("I can't get this file/URL!")

            try:
                if equal_to:
                    await resp.content.readexactly(
                        limit + 1
                    )  # we want this to error out even if the file is exactly the limit
                    raise ipy.errors.BadArgument(
                        "The file/URL given is over"
                        f" {humanize.naturalsize(limit, binary=True)}!"
                    )
                else:
                    await resp.content.readexactly(limit)
                    raise ipy.errors.BadArgument(
                        "The file/URL given is at or over"
                        f" {humanize.naturalsize(limit, binary=True)}!"
                    )

            except asyncio.IncompleteReadError as e:
                # essentially, we're exploting the fact that readexactly will error out if
                # the url given is less than the limit
                return e.partial


class CustomPartialEmojiConverter(ipy.Converter[ipy.PartialEmoji]):
    @staticmethod
    async def convert(ctx: ipy.BaseContext, argument: str) -> ipy.PartialEmoji:
        if match := DISCORD_EMOJI_REGEX.match(argument):
            emoji_animated = bool(match[1])
            emoji_name = match[2]
            emoji_id = int(match[3])

            return ipy.PartialEmoji(
                id=emoji_id, name=emoji_name, animated=emoji_animated
            )

        raise ipy.errors.BadArgument(
            f'Couldn\'t convert "{argument}" to a Discord emoji.'
        )


def get_emoji_url(emoji: ipy.PartialEmoji):
    fmt = "gif" if emoji.animated else "png"
    return f"{ipy.Asset.BASE}/emojis/{emoji.id}.{fmt}"
