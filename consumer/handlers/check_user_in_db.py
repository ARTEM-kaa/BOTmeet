from sqlalchemy import select
from consumer.storage.db import async_session
from src.model.models import User
from src.storage.rabbit import channel_pool
import aio_pika
import msgpack
from aio_pika import ExchangeType
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

async def check_registration(body: dict) -> bool:
    user_id = body.get('user_id')
    logger.info(f"Checking registration for user ID: {user_id}")
    
    try:
        async with async_session() as session:
            logger.debug(f"Executing query for user {user_id}")
            result = await session.execute(
                select(User).where(User.tg_id == user_id)
            )
            user = result.scalar_one_or_none()
        
            response_body = {
                'user_id': user_id,
                'exists': user is not None,
            }
            logger.debug(f"Registration check result for {user_id}: {'exists' if user else 'not exists'}")
        
        try:
            async with channel_pool.acquire() as channel:
                logger.debug(f"Creating exchange for user {user_id}")
                exchange = await channel.declare_exchange('user_check', ExchangeType.TOPIC, durable=True)

                queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)

                await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))

                logger.debug(f"Sending response for user {user_id}")
                await exchange.publish(
                    aio_pika.Message(msgpack.packb(response_body)),
                    routing_key=settings.USER_QUEUE.format(user_id=user_id),
                )
                logger.info(f"Response sent successfully for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to send RabbitMQ response for user {user_id}: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Error during registration check for user {user_id}: {str(e)}")
        raise
    
    return user is not None
