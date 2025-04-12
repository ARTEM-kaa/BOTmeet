from model.models import User, Photo
from storage.db import async_session
from datetime import datetime


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

        await session.commit()
