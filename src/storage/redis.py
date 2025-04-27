from redis.asyncio import Redis
from config.settings import settings
from aiogram.fsm.storage.redis import RedisStorage


redis_storage = RedisStorage(
    redis=Redis.from_url(settings.redis_url)
)
