from redis.asyncio import Redis
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class PhotoCache:
    def __init__(self):
        logger.info("Инициализация кэша фотографий")
        self.redis = Redis.from_url(
            settings.redis_url,
            decode_responses=False
        )

    async def cache_photo(self, photo_url: str, photo_data: bytes):
        try:
            logger.debug(f"Кэширование фото по URL: {photo_url}")
            await self.redis.setex(
                f"photo:{photo_url}",
                settings.REDIS_EXPIRE_SECONDS,
                photo_data
            )
            logger.debug(f"Фото успешно закэшировано: {photo_url}")
        except Exception as e:
            logger.error(f"Ошибка при кэшировании фото {photo_url}: {str(e)}")
            raise

    async def get_cached_photo(self, photo_url: str) -> bytes | None:
        try:
            logger.debug(f"Получение фото из кэша: {photo_url}")
            photo_data = await self.redis.get(f"photo:{photo_url}")
            if photo_data:
                logger.debug(f"Фото найдено в кэше: {photo_url}")
            else:
                logger.debug(f"Фото отсутствует в кэше: {photo_url}")
            return photo_data
        except Exception as e:
            logger.error(f"Ошибка при получении фото из кэша {photo_url}: {str(e)}")
            raise

    async def close(self):
        try:
            logger.info("Закрытие соединения с Redis")
            await self.redis.close()
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с Redis: {str(e)}")
            raise

photo_cache = PhotoCache()
