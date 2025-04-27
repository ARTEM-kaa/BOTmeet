import msgpack
from sqlalchemy import select, delete, update, func
from datetime import datetime
from typing import Optional
import logging
from consumer.storage.db import async_session
from src.model.models import User, Like
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings

logger = logging.getLogger(__name__)

async def process_like(body: dict):
    from_user_tg_id = body.get('from_user_tg_id')
    to_user_id = body.get('to_user_id')
    is_like = body.get('is_like', True)
    
    logger.info(f"Processing {'like' if is_like else 'dislike'} from user {from_user_tg_id} to user {to_user_id}")
    
    response = {
        'from_user_tg_id': from_user_tg_id,
        'to_user_id': to_user_id,
        'is_like': is_like,
        'action': 'like_processed'
    }
    
    try:
        async with async_session() as session:
            logger.debug(f"Fetching from_user info for tg_id: {from_user_tg_id}")
            from_user_result = await session.execute(select(User).where(User.tg_id == from_user_tg_id))
            from_user = from_user_result.scalar_one()
            from_user_id = from_user.id

            logger.debug(f"Deleting existing likes between users {from_user_id} and {to_user_id}")
            await session.execute(
                delete(Like)
                .where(
                    Like.from_user_id == from_user_id,
                    Like.to_user_id == to_user_id
                )
            )

            logger.debug(f"Creating new {'like' if is_like else 'dislike'} record")
            like = Like(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                is_like=is_like,
                liked_at=datetime.utcnow()
            )
            session.add(like)
            
            await session.commit()
            logger.debug("Like record successfully committed")

            if is_like:
                logger.debug("Processing like - updating rating and checking for match")
                await _update_user_rating(session, to_user_id)
                matched_user = await _check_match(session, from_user_id, to_user_id)
                if matched_user:
                    logger.info(f"Match found between users {from_user_id} and {to_user_id}")
                    response['match'] = True
                    response['matched_user'] = {
                        'tg_id': matched_user.tg_id,
                        'tg_username': matched_user.tg_username,
                        'firstname': matched_user.firstname,
                        'lastname': matched_user.lastname
                    }
                    response['from_user_data'] = {
                        'tg_id': from_user.tg_id,
                        'tg_username': from_user.tg_username,
                        'firstname': from_user.firstname,
                        'lastname': from_user.lastname
                    }
            else:
                logger.debug("Processing dislike - updating rating")
                await _update_user_rating(session, to_user_id)
            
            response['status'] = 'success'
            logger.info(f"Successfully processed {'like' if is_like else 'dislike'}")
            
    except Exception as e:
        logger.error(f"Error processing like: {str(e)}", exc_info=True)
        response.update({
            'status': 'error',
            'error': str(e)
        })

    try:
        await _publish_response(response)
        logger.debug("Successfully published response")
    except Exception as e:
        logger.error(f"Failed to publish response: {str(e)}", exc_info=True)
        raise


async def _update_user_rating(session, user_id: int):
    logger.debug(f"Updating rating for user {user_id}")

    likes = await session.execute(
        select(func.count()).where(
            Like.to_user_id == user_id,
            Like.is_like == True
        )
    )
    like_count = likes.scalar() or 0
    logger.debug(f"User {user_id} has {like_count} likes")

    dislikes = await session.execute(
        select(func.count()).where(
            Like.to_user_id == user_id,
            Like.is_like == False
        )
    )
    dislike_count = dislikes.scalar() or 0
    logger.debug(f"User {user_id} has {dislike_count} dislikes")

    base_rating = 2.5
    like_weight = 0.1
    dislike_weight = 0.15
    
    new_rating = base_rating + (like_count * like_weight) - (dislike_count * dislike_weight)
    new_rating = max(0.0, min(5.0, new_rating))
    logger.debug(f"New rating for user {user_id}: {new_rating:.2f}")

    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            rating=new_rating,
            like_count=like_count,
            dislike_count=dislike_count
        )
    )


async def _check_match(session, user1_id: int, user2_id: int) -> Optional[int]:
    logger.debug(f"Checking for match between users {user1_id} and {user2_id}")
    
    mutual_like = await session.execute(
        select(Like)
        .where(
            Like.from_user_id == user2_id,
            Like.to_user_id == user1_id,
            Like.is_like == True
        )
    )
    
    if mutual_like.scalar():
        logger.debug(f"Mutual like found between users {user1_id} and {user2_id}")
        return await session.get(User, user2_id)
    
    logger.debug("No mutual like found")
    return None


async def _publish_response(response: dict):
    user_id = response['from_user_tg_id']
    logger.debug(f"Publishing response for user {user_id}")
    
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            'likes_updates',
            ExchangeType.TOPIC,
            durable=True
        )
        
        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb(response),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    'user_id': str(user_id),
                    'action': response['action']
                }
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_id)
        )
