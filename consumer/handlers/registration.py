from datetime import datetime
from sqlalchemy.exc import IntegrityError
from consumer.storage.db import async_session
from src.model.models import User, Photo, Preference

async def create_user_profile(body: dict) -> None:
    user_id = body['user_id']
    user_data = body['user_data']
    tg_username = body.get('tg_username')
    
    full_name = user_data["full_name"].split()
    firstname, lastname, mname = full_name[1], full_name[0], full_name[2]

    async with async_session() as session:
        async with session.begin():
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

            photo = Photo(
                user_id=user.id,
                url=user_data["photo"]
            )
            session.add(photo)
            
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
            await session.commit()
        except IntegrityError:
            await session.rollback()
