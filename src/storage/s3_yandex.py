import aioboto3
import uuid
from config.settings import settings


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
        return f"{settings.ENDPOINT_URL}/{settings.BUCKET_NAME}/{object_key}"
