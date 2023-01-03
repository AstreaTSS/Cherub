from dotenv import load_dotenv

load_dotenv()

import asyncio
import contextlib
import logging
import os

import naff
import tansy

tansy.install_naff_speedups()

import common.utils as utils


logger = logging.getLogger("cherub")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ["LOG_FILE_PATH"], encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

intents = naff.Intents.new(
    guilds=True,
    guild_emojis_and_stickers=True,
    messages=True,
)
mentions = naff.AllowedMentions.all()
activity = naff.Activity.create(
    name="in the ethereal realm", type=naff.ActivityType.WATCHING
)
bot = utils.CherubBase(
    intents=intents,
    allowed_mentions=mentions,
    activity=activity,
    logger=logger,
    sync_interactions=False,
    send_command_tracebacks=False,
)
bot.cache.enable_emoji_cache = True
bot.cache.emoji_cache = {}

bot.color = naff.Color(int(os.environ["BOT_COLOR"]))  # #000000, aka 0
bot.init_load = True


@naff.listen(disable_default_listeners=True)
async def on_error(event: naff.events.Error):
    await utils.error_handle(bot, event.error, event.ctx)


@naff.listen("startup")
async def on_startup():
    bot.fully_ready.set()


@naff.listen("ready")
async def on_ready():
    utcnow = naff.Timestamp.utcnow()
    time_format = f"<t:{int(utcnow.timestamp())}:f>"

    connect_msg = (
        f"Logged in at {time_format}!"
        if bot.init_load == True
        else f"Reconnected at {time_format}!"
    )

    await bot.owner.send(connect_msg)

    bot.init_load = False
    await bot.change_presence(activity=activity)


async def start():
    bot.fully_ready = asyncio.Event()

    ext_list = utils.get_all_extensions(os.environ.get("DIRECTORY_OF_BOT"))
    for ext in ext_list:
        bot.load_extension(ext)

    await bot.astart(os.environ["MAIN_TOKEN"])


loop_factory = None

with contextlib.suppress(ImportError):
    import uvloop  # type: ignore

    loop_factory = uvloop.new_event_loop


with asyncio.Runner(loop_factory=loop_factory) as runner:
    asyncio.run(start())
