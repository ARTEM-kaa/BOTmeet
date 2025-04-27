import aioboto3
import uuid
import aiohttp
from config.settings import settings
from src.storage.redis_client import photo_cache
from typing import Optional

async def upload_photo_to_s3(file: bytes, filename: str) -> str:
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

        await photo_cache.cache_photo(photo_url, file)
        
        return photo_url

async def get_photo_with_cache(photo_url: str) -> Optional[bytes]:
    cached_photo = await photo_cache.get_cached_photo(photo_url)
    if cached_photo:
        return cached_photo

    async with aiohttp.ClientSession() as session:
        async with session.get(photo_url) as resp:
            if resp.status == 200:
                photo_data = await resp.read()
                await photo_cache.cache_photo(photo_url, photo_data)
                return photo_data
    return None
