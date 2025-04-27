from datetime import datetime
from sqlalchemy.exc import IntegrityError
import logging
from consumer.storage.db import async_session
from src.model.models import User, Photo, Preference

logger = logging.getLogger(__name__)

async def create_user_profile(body: dict) -> None:
    user_id = body['user_id']
    user_data = body['user_data']
    tg_username = body.get('tg_username')
    
    logger.info(f"Creating new user profile for tg_id: {user_id}")
    logger.debug(f"User data: {user_data}")

    try:
        full_name = user_data["full_name"].split()
        firstname, lastname, mname = full_name[1], full_name[0], full_name[2]
        logger.debug(f"Parsed name components: firstname={firstname}, lastname={lastname}, mname={mname}")

        async with async_session() as session:
            async with session.begin():
                logger.debug("Creating User record")
                user = User(
                    tg_id=user_id,
                    firstname=firstname,
                    lastname=lastname,
                    mname=mname,
                    age=int(user_data["age"]),
                    gender=user_data["gender"],
                    bio=user_data["bio"],
                    rating=2.5,
                    like_count=0,
                    dislike_count=0,
                    created_at=datetime.utcnow(),
                    tg_username=tg_username
                )
                session.add(user)
                await session.flush()
                logger.debug(f"User created with ID: {user.id}")

                logger.debug("Creating Photo record")
                photo = Photo(
                    user_id=user.id,
                    url=user_data["photo"]
                )
                session.add(photo)
                
                logger.debug("Creating default Preferences")
                preferences = Preference(
                    user_id=user.id,
                    preferred_gender="Любой",
                    min_age=10,
                    max_age=110,
                    min_rating=0.0,
                    max_rating=5.0,
                )
                session.add(preferences)

            try:
                logger.debug("Committing transaction")
                await session.commit()
                logger.info(f"Successfully created profile for user {user_id}")
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"Integrity error creating user {user_id}: {str(e)}")
                raise
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating user {user_id}: {str(e)}")
                raise

    except KeyError as e:
        logger.error(f"Missing required field in user data: {str(e)}")
        raise
    except IndexError as e:
        logger.error(f"Invalid full_name format: {user_data['full_name']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating user profile: {str(e)}")
        raise
