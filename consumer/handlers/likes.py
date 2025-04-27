import msgpack
from sqlalchemy import select, delete, update, func
from datetime import datetime
from typing import Optional

from consumer.storage.db import async_session
from src.model.models import User, Like
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings


async def process_like(body: dict):
    from_user_tg_id = body.get('from_user_tg_id')
    to_user_id = body.get('to_user_id')
    is_like = body.get('is_like', True)
    
    response = {
        'from_user_tg_id': from_user_tg_id,
        'to_user_id': to_user_id,
        'is_like': is_like,
        'action': 'like_processed'
    }
    
    try:
        async with async_session() as session:
            from_user_result = await session.execute(select(User).where(User.tg_id == from_user_tg_id))
            from_user = from_user_result.scalar_one()
            from_user_id = from_user.id

            await session.execute(
                delete(Like)
                .where(
                    Like.from_user_id == from_user_id,
                    Like.to_user_id == to_user_id
                )
            )

            like = Like(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                is_like=is_like,
                liked_at=datetime.utcnow()
            )
            session.add(like)
            
            await session.commit()

            if is_like:
                await _update_user_rating(session, to_user_id)
                matched_user = await _check_match(session, from_user_id, to_user_id)
                if matched_user:
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
                await _update_user_rating(session, to_user_id)
            
            response['status'] = 'success'
            
    except Exception as e:
        response.update({
            'status': 'error',
            'error': str(e)
        })

    await _publish_response(response)


async def _update_user_rating(session, user_id: int):
    likes = await session.execute(
        select(func.count()).where(
            Like.to_user_id == user_id,
            Like.is_like == True
        )
    )
    like_count = likes.scalar() or 0

    dislikes = await session.execute(
        select(func.count()).where(
            Like.to_user_id == user_id,
            Like.is_like == False
        )
    )
    dislike_count = dislikes.scalar() or 0

    base_rating = 2.5
    like_weight = 0.1
    dislike_weight = 0.15
    
    new_rating = base_rating + (like_count * like_weight) - (dislike_count * dislike_weight)
    new_rating = max(0.0, min(5.0, new_rating))

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
    mutual_like = await session.execute(
        select(Like)
        .where(
            Like.from_user_id == user2_id,
            Like.to_user_id == user1_id,
            Like.is_like == True
        )
    )
    
    if mutual_like.scalar():
        return await session.get(User, user2_id)
    return None


async def _publish_response(response: dict):
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
                    'user_id': str(response['from_user_tg_id']),
                    'action': response['action']
                }
            ),
            routing_key=settings.USER_QUEUE.format(user_id=response['from_user_tg_id'])
        )
