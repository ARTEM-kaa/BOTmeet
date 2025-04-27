import msgpack
from sqlalchemy import update, select

from consumer.storage.db import async_session
from src.model.models import User, Preference
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings


async def update_preferences_handler(body: dict):
    user_tg_id = body.get('user_tg_id')
    data = body.get('data')
    
    if not user_tg_id or not data:
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User.id).where(User.tg_id == user_tg_id))
        user_id = result.scalar_one()

        await session.execute(
            update(Preference)
            .where(Preference.user_id == user_id)
            .values(**data))
        
        await session.commit()
        
    response_body = {
        'user_tg_id': user_tg_id,
        'status': 'updated',
        'updated_fields': list(data.keys())
    }
    
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            'preferences_updates', 
            ExchangeType.TOPIC, 
            durable=True
        )
        
        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb(response_body),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
        )
