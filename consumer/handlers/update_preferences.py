import msgpack
from sqlalchemy import update, select
import logging
from consumer.storage.db import async_session
from src.model.models import User, Preference
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings

logger = logging.getLogger(__name__)

async def update_preferences_handler(body: dict):
    user_tg_id = body.get('user_tg_id')
    data = body.get('data')
    
    logger.info(f"Processing preferences update for user {user_tg_id}")
    logger.debug(f"Update data: {data}")

    if not user_tg_id or not data:
        logger.warning("Invalid request: missing user_tg_id or data")
        return
    
    try:
        async with async_session() as session:
            logger.debug("Fetching user ID from database")
            result = await session.execute(
                select(User.id).where(User.tg_id == user_tg_id))
            user_id = result.scalar_one()
            logger.debug(f"Found user ID: {user_id}")

            logger.debug("Updating preferences in database")
            result = await session.execute(
                update(Preference)
                .where(Preference.user_id == user_id)
                .values(**data)
            )
            
            if result.rowcount == 0:
                logger.warning(f"No preferences found for user {user_id}")
                raise ValueError("Preferences record not found")
                
            await session.commit()
            logger.info("Preferences updated successfully")

            response_body = {
                'user_tg_id': user_tg_id,
                'status': 'updated',
                'updated_fields': list(data.keys())
            }

            logger.debug("Publishing update notification")
            async with channel_pool.acquire() as channel:
                exchange = await channel.declare_exchange(
                    'preferences_updates', 
                    ExchangeType.TOPIC, 
                    durable=True
                )
                
                await exchange.publish(
                    aio_pika.Message(
                        body=msgpack.packb(response_body),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        headers={
                            'user_id': str(user_tg_id),
                            'action': 'preferences_updated'
                        }
                    ),
                    routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
                )
            logger.info("Update notification sent successfully")

    except Exception as e:
        logger.error(f"Failed to update preferences: {str(e)}", exc_info=True)

        error_response = {
            'user_tg_id': user_tg_id,
            'status': 'error',
            'error': str(e)
        }
        
        try:
            async with channel_pool.acquire() as channel:
                exchange = await channel.declare_exchange(
                    'preferences_updates', 
                    ExchangeType.TOPIC, 
                    durable=True
                )
                
                await exchange.publish(
                    aio_pika.Message(
                        body=msgpack.packb(error_response),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
                )
            logger.warning("Error notification sent successfully")
        except Exception as pub_err:
            logger.error(f"Failed to send error notification: {str(pub_err)}")
        
        raise
