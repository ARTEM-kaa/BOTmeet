from model.models import User, Photo, Preference
from storage.db import async_session
from datetime import datetime
from sqlalchemy import select, update



async def create_user_profile(user_id: int, data: dict):
    full_name = data["full_name"].split()
    firstname, lastname, mname = full_name[1], full_name[0], full_name[2]

    async with async_session() as session:
        async with session.begin():
            user = User(
                tg_id=user_id,
                firstname=firstname,
                lastname=lastname,
                mname=mname,
                age=int(data["age"]),
                gender=data["gender"],
                bio=data["bio"],
                created_at=datetime.utcnow()
            )
            session.add(user)
            await session.flush()

            photo = Photo(
                user_id=user.id,
                url=data["photo"]
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

        await session.commit()


async def update_user_field(user_tg_id: int, data: dict):
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.tg_id == user_tg_id)
            .values(**data)
        )
        await session.commit()


async def update_user_photo(user_id: int, url: str):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one()
        await session.execute(
            update(Photo).where(Photo.user_id == user.id).values(url=url)
        )
        await session.commit()


async def update_user_preferences(user_tg_id: int, data: dict):
    async with async_session() as session:
        result = await session.execute(
            select(User.id).where(User.tg_id == user_tg_id)
        )
        user_id = result.scalar_one()

        await session.execute(
            update(Preference)
            .where(Preference.user_id == user_id)
            .values(**data)
        )

        await session.commit()