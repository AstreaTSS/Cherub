import datetime
import typing

from beanie import Document
from beanie import Indexed


class Config(Document):
    guild_id: typing.Annotated[str, Indexed(str)]
    pinboards: dict[str, str]

    class Settings:
        use_cache = True
        cache_expiration_time = datetime.timedelta(seconds=10)
        cache_capacity = 5
