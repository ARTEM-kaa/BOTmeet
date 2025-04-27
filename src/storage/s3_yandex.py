import aioboto3
import uuid
import aiohttp
from config.settings import settings
from src.storage.redis_client import photo_cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def upload_photo_to_s3(file: bytes, filename: str) -> str:
    try:
        logger.info(f"Начало загрузки фото в S3: {filename}")
        session = aioboto3.Session()
        object_key = f"avatars/{uuid.uuid4()}_{filename}"
        
        async with session.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.REGION_NAME,
            endpoint_url=settings.ENDPOINT_URL,
        ) as s3:
            await s3.put_object(Bucket=settings.BUCKET_NAME, Key=object_key, Body=file)
            photo_url = f"{settings.ENDPOINT_URL}/{settings.BUCKET_NAME}/{object_key}"

            logger.info(f"Фото успешно загружено в S3: {photo_url}")
            
            try:
                await photo_cache.cache_photo(photo_url, file)
                logger.debug(f"Фото закэшировано: {photo_url}")
            except Exception as e:
                logger.error(f"Ошибка кэширования фото {photo_url}: {str(e)}")
            
            return photo_url
            
    except Exception as e:
        logger.error(f"Ошибка загрузки фото в S3: {str(e)}")
        raise

async def get_photo_with_cache(photo_url: str) -> Optional[bytes]:
    try:
        logger.debug(f"Попытка получить фото из кэша: {photo_url}")
        cached_photo = await photo_cache.get_cached_photo(photo_url)
        if cached_photo:
            logger.debug(f"Фото получено из кэша: {photo_url}")
            return cached_photo

        logger.debug(f"Фото отсутствует в кэше, загрузка из S3: {photo_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url) as resp:
                if resp.status == 200:
                    photo_data = await resp.read()
                    try:
                        await photo_cache.cache_photo(photo_url, photo_data)
                        logger.debug(f"Фото загружено из S3 и закэшировано: {photo_url}")
                    except Exception as e:
                        logger.error(f"Ошибка кэширования загруженного фото {photo_url}: {str(e)}")
                    return photo_data
                else:
                    logger.warning(f"Не удалось загрузить фото {photo_url}, статус: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Ошибка получения фото {photo_url}: {str(e)}")
        return None
