import msgpack
from sqlalchemy import select, update

from consumer.storage.db import async_session
from src.model.models import User, Photo
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings
from src.storage.s3_yandex import upload_photo_to_s3


async def process_photo_update(body: dict):
    user_tg_id = body.get('user_tg_id')
    file_data = body.get('file_data')
    filename = body.get('filename')

    s3_url = await upload_photo_to_s3(file=file_data, filename=filename)
    
    async with async_session() as session:
        user = await session.execute(select(User).where(User.tg_id == user_tg_id))
        user = user.scalar_one()
        
        await session.execute(
            update(Photo)
            .where(Photo.user_id == user.id)
            .values(url=s3_url))
        
        await session.commit()
    
    response = {
        'status': 'success',
        'user_tg_id': user_tg_id,
        'photo_url': s3_url,
        'action': 'photo_updated'
    }
    
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange('photo_updates', ExchangeType.TOPIC, durable=True)
        
        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb(response),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
        )
