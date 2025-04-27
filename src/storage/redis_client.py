from redis.asyncio import Redis
from config.settings import settings

class PhotoCache:
    def __init__(self):
        self.redis = Redis.from_url(
            settings.redis_url,
            decode_responses=False
        )

    async def cache_photo(self, photo_url: str, photo_data: bytes):
        await self.redis.setex(
            f"photo:{photo_url}",
            settings.REDIS_EXPIRE_SECONDS,
            photo_data
        )

    async def get_cached_photo(self, photo_url: str) -> bytes | None:
        return await self.redis.get(f"photo:{photo_url}")

    async def close(self):
        await self.redis.close()

photo_cache = PhotoCache()