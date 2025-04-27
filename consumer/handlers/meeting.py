import msgpack
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from consumer.storage.db import async_session
from src.model.models import User, Like, Preference
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings


async def process_get_next_profile(body: dict):
    current_tg_id = body.get('current_tg_id')
    commented_but_not_rated = body.get('commented_but_not_rated')
    
    async with async_session() as session:
        if commented_but_not_rated:
            return commented_but_not_rated

        user_result = await session.execute(
            select(User).where(User.tg_id == current_tg_id))
        current_user = user_result.scalar_one_or_none()
        if not current_user:
            return None

        interacted = await session.execute(
            select(Like.to_user_id).where(Like.from_user_id == current_user.id)
        )
        excluded_ids = {id for (id,) in interacted.all()} | {current_user.id}

        pref_result = await session.execute(
            select(Preference).where(Preference.user_id == current_user.id)
        )
        prefs = pref_result.scalar_one_or_none()

        query = (
            select(User)
            .options(selectinload(User.photo))
            .where(
                User.id.not_in(excluded_ids),
                User.photo != None
            )
        )

        if prefs:
            if prefs.preferred_gender and prefs.preferred_gender != "Любой":
                query = query.where(User.gender == prefs.preferred_gender)
            
            if prefs.min_age is not None:
                query = query.where(User.age >= prefs.min_age)
            if prefs.max_age is not None:
                query = query.where(User.age <= prefs.max_age)

            if prefs.min_rating is not None:
                query = query.where(User.rating >= prefs.min_rating)
            if prefs.max_rating is not None:
                query = query.where(User.rating <= prefs.max_rating)

        result = await session.execute(query.order_by(func.random()))
        user = result.scalars().first()

        if user:
            full_name = " ".join(filter(None, [user.lastname, user.firstname, user.mname]))
            profile_data = {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "mname": user.mname,
                "full_name": full_name,
                "photo": user.photo.url,
                "bio": user.bio,
                "age": user.age,
                "gender": user.gender,
                "rating": float(user.rating)
            }

            response = {
                'status': 'success',
                'profile': profile_data,
                'user_tg_id': current_tg_id,
                'action': 'next_profile'
            }
        else:
            response = {
                'status': 'empty',
                'user_tg_id': current_tg_id,
                'action': 'next_profile'
            }

        async with channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('meeting_updates', ExchangeType.TOPIC, durable=True
            )
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(response),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=settings.USER_QUEUE.format(user_id=current_tg_id)
            )
