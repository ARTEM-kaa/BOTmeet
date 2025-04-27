from sqlalchemy import select
from consumer.storage.db import async_session
from src.model.models import User
from src.storage.rabbit import channel_pool
import aio_pika
import msgpack
from aio_pika import ExchangeType
from config.settings import settings


async def check_registration(body: dict) -> bool:
    user_id = body.get('user_id')
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user = result.scalar_one_or_none()
    
        response_body = {
            'user_id': user_id,
            'exists': user is not None,
        }
    
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange('user_check', ExchangeType.TOPIC, durable=True)

        queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)

        await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))

        await exchange.publish(
            aio_pika.Message(msgpack.packb(response_body)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id),
        )
