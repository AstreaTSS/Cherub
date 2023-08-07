from dotenv import load_dotenv

load_dotenv()

import asyncio
import contextlib
import logging
import os

import interactions as ipy
from interactions.ext import prefixed_commands as prefixed
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

import common.utils as utils
import common.models as models

logger = logging.getLogger("cherub")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ["LOG_FILE_PATH"], encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

intents = ipy.Intents.new(
    guilds=True,
    guild_emojis_and_stickers=True,
    messages=True,
    message_content=True,
)
mentions = ipy.AllowedMentions.all()
activity = ipy.Activity.create(
    name="in the ethereal realm", type=ipy.ActivityType.WATCHING
)
bot = utils.CherubBase(
    intents=intents,
    allowed_mentions=mentions,
    activity=activity,
    logger=logger,
    sync_interactions=False,
    sync_ext=False,
    send_command_tracebacks=False,
    auto_defer=ipy.AutoDefer(enabled=True, time_until_defer=0),
)
bot.cache.enable_emoji_cache = True
bot.cache.emoji_cache = {}

bot.color = ipy.Color(int(os.environ["BOT_COLOR"]))  # #000000, aka 0
bot.init_load = True

prefixed.setup(bot)


@ipy.listen(disable_default_listeners=True)
async def on_error(event: ipy.events.Error):
    await utils.error_handle(bot, event.error, event.ctx)


@ipy.listen("startup")
async def on_startup():
    bot.fully_ready.set()


@ipy.listen("ready")
async def on_ready():
    utcnow = ipy.Timestamp.utcnow()
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
    client = AsyncIOMotorClient(os.environ["MONGO_DB_URL"])
    await init_beanie(client.Cherub, document_models=[models.Config])

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
