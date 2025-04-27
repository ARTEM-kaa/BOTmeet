import msgpack
from sqlalchemy import select, update
import logging
from consumer.storage.db import async_session
from src.model.models import User, Photo
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings
from src.storage.s3_yandex import upload_photo_to_s3, get_photo_with_cache

logger = logging.getLogger(__name__)

async def process_photo_update(body: dict):
    user_tg_id = body.get('user_tg_id')
    file_data = body.get('file_data')
    filename = body.get('filename')
    
    logger.info(f"Processing photo update for user {user_tg_id}")
    logger.debug(f"Filename: {filename}, Data size: {len(file_data) if file_data else 0} bytes")

    try:
        logger.debug("Uploading photo to S3 storage")
        s3_url = await upload_photo_to_s3(file=file_data, filename=filename)
        logger.info(f"Photo uploaded successfully to {s3_url}")

        logger.debug("Updating photo URL in database")
        async with async_session() as session:
            user = await session.execute(select(User).where(User.tg_id == user_tg_id))
            user = user.scalar_one()
            
            await session.execute(
                update(Photo)
                .where(Photo.user_id == user.id)
                .values(url=s3_url)
            )
            
            await session.commit()
            logger.debug("Database update committed successfully")

        response = {
            'status': 'success',
            'user_tg_id': user_tg_id,
            'photo_url': s3_url,
            'action': 'photo_updated'
        }

        logger.debug("Publishing photo update notification")
        async with channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange(
                'photo_updates',
                ExchangeType.TOPIC,
                durable=True
            )
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(response),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
            )
        logger.info("Photo update processed successfully")

    except Exception as e:
        logger.error(f"Failed to process photo update: {str(e)}", exc_info=True)
        response = {
            'status': 'error',
            'user_tg_id': user_tg_id,
            'error': str(e),
            'action': 'photo_update_failed'
        }

        try:
            async with channel_pool.acquire() as channel:
                exchange = await channel.declare_exchange(
                    'photo_updates',
                    ExchangeType.TOPIC,
                    durable=True
                )
                
                await exchange.publish(
                    aio_pika.Message(
                        body=msgpack.packb(response),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=settings.USER_QUEUE.format(user_id=user_tg_id)
                )
            logger.warning("Error notification sent successfully")
        except Exception as pub_err:
            logger.error(f"Failed to send error notification: {str(pub_err)}")
        
        raise
