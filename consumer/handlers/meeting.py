import msgpack
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import logging
from consumer.storage.db import async_session
from src.model.models import User, Like, Preference
from consumer.storage.rabbit import channel_pool
import aio_pika
from aio_pika import ExchangeType
from config.settings import settings

logger = logging.getLogger(__name__)

async def process_get_next_profile(body: dict):
    current_tg_id = body.get('current_tg_id')
    commented_but_not_rated = body.get('commented_but_not_rated')
    
    logger.info(f"Processing next profile request for user {current_tg_id}")
    logger.debug(f"Commented but not rated: {commented_but_not_rated}")

    async with async_session() as session:
        try:
            if commented_but_not_rated:
                logger.info("Returning previously commented profile")
                return commented_but_not_rated

            logger.debug("Fetching current user info")
            user_result = await session.execute(
                select(User).where(User.tg_id == current_tg_id))
            current_user = user_result.scalar_one_or_none()
            
            if not current_user:
                logger.warning(f"User {current_tg_id} not found in database")
                return None

            logger.debug("Fetching interacted user IDs")
            interacted = await session.execute(
                select(Like.to_user_id).where(Like.from_user_id == current_user.id)
            )
            excluded_ids = {id for (id,) in interacted.all()} | {current_user.id}
            logger.debug(f"Excluded user IDs: {excluded_ids}")

            logger.debug("Fetching user preferences")
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
                logger.debug("Applying preference filters")
                if prefs.preferred_gender and prefs.preferred_gender != "Любой":
                    logger.debug(f"Gender filter: {prefs.preferred_gender}")
                    query = query.where(User.gender == prefs.preferred_gender)
                
                if prefs.min_age is not None:
                    logger.debug(f"Min age filter: {prefs.min_age}")
                    query = query.where(User.age >= prefs.min_age)
                if prefs.max_age is not None:
                    logger.debug(f"Max age filter: {prefs.max_age}")
                    query = query.where(User.age <= prefs.max_age)

                if prefs.min_rating is not None:
                    logger.debug(f"Min rating filter: {prefs.min_rating}")
                    query = query.where(User.rating >= prefs.min_rating)
                if prefs.max_rating is not None:
                    logger.debug(f"Max rating filter: {prefs.max_rating}")
                    query = query.where(User.rating <= prefs.max_rating)

            logger.debug("Executing random profile query")
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
                logger.info(f"Found matching profile: {user.id}")

                response = {
                    'status': 'success',
                    'profile': profile_data,
                    'user_tg_id': current_tg_id,
                    'action': 'next_profile'
                }
            else:
                logger.info("No matching profiles found")
                response = {
                    'status': 'empty',
                    'user_tg_id': current_tg_id,
                    'action': 'next_profile'
                }

            try:
                logger.debug("Publishing response via RabbitMQ")
                async with channel_pool.acquire() as channel:
                    exchange = await channel.declare_exchange(
                        'meeting_updates', 
                        ExchangeType.TOPIC, 
                        durable=True
                    )
                    
                    await exchange.publish(
                        aio_pika.Message(
                            body=msgpack.packb(response),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        ),
                        routing_key=settings.USER_QUEUE.format(user_id=current_tg_id)
                    )
                logger.info("Response successfully published")
            except Exception as e:
                logger.error(f"Failed to publish response: {str(e)}")
                raise

            return response

        except Exception as e:
            logger.error(f"Error processing next profile request: {str(e)}")
            raise
