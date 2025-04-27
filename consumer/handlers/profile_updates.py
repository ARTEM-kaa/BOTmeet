import msgpack
from sqlalchemy import update
from typing import Dict, Any

from consumer.storage.db import async_session
from src.model.models import User
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings


async def process_profile_update(body: Dict[str, Any]):
    user_tg_id = body.get('user_tg_id')
    update_data = body.get('data')
    action_type = body.get('action_type')
    
    try:
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.tg_id == user_tg_id)
                .values(**update_data)
            )
            await session.commit()

            response = {
                'status': 'success',
                'user_tg_id': user_tg_id,
                'action': 'profile_updated',
                'action_type': action_type,
                'updated_fields': list(update_data.keys())
            }
            
    except Exception as e:
        response = {
            'status': 'error',
            'user_tg_id': user_tg_id,
            'error': str(e),
            'action': 'profile_update_error'
        }

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange('profile_updates', ExchangeType.TOPIC, durable=True)
        
        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb(response),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
        )
