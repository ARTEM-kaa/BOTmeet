import msgpack
from sqlalchemy import update
from typing import Dict, Any
import logging
from consumer.storage.db import async_session
from src.model.models import User
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings

logger = logging.getLogger(__name__)

async def process_profile_update(body: Dict[str, Any]):
    user_tg_id = body.get('user_tg_id')
    update_data = body.get('data')
    action_type = body.get('action_type')
    
    logger.info(f"Processing profile update for user {user_tg_id}")
    logger.debug(f"Update data: {update_data}, Action type: {action_type}")

    try:
        async with async_session() as session:
            logger.debug("Executing database update")
            result = await session.execute(
                update(User)
                .where(User.tg_id == user_tg_id)
                .values(**update_data)
            )
            
            if result.rowcount == 0:
                logger.warning(f"No user found with tg_id: {user_tg_id}")
                raise ValueError(f"User {user_tg_id} not found")
                
            await session.commit()
            logger.info("Profile update committed successfully")

            response = {
                'status': 'success',
                'user_tg_id': user_tg_id,
                'action': 'profile_updated',
                'action_type': action_type,
                'updated_fields': list(update_data.keys())
            }
            
    except Exception as e:
        logger.error(f"Failed to update profile: {str(e)}", exc_info=True)
        response = {
            'status': 'error',
            'user_tg_id': user_tg_id,
            'error': str(e),
            'action': 'profile_update_error'
        }

    try:
        logger.debug("Publishing update response")
        async with channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange(
                'profile_updates', 
                ExchangeType.TOPIC, 
                durable=True
            )
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(response),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={
                        'user_id': str(user_tg_id),
                        'action': response['action']
                    }
                ),
                routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
            )
        logger.info("Response published successfully")
    except Exception as e:
        logger.critical(f"Failed to publish response: {str(e)}")
        raise
