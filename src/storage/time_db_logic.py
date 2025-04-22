from model.models import User, Photo, Preference, Rating, Like
from storage.db import async_session
from datetime import datetime
from sqlalchemy import select, update, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload


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
                rating=0.0,
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


async def get_next_profile(current_tg_id: int):
    async with async_session() as session:
        # Получаем текущего пользователя
        user_result = await session.execute(
            select(User).where(User.tg_id == current_tg_id)
        )
        current_user = user_result.scalar_one_or_none()
        if not current_user:
            return None

        # Получаем предпочтения
        pref_result = await session.execute(
            select(Preference).where(Preference.user_id == current_user.id)
        )
        prefs = pref_result.scalar_one_or_none()

        # Получаем ID пользователей, с которыми уже взаимодействовали
        interacted = await session.execute(
            select(Like.to_user_id).where(Like.from_user_id == current_user.id)
            .union(
                select(Rating.to_user_id).where(Rating.from_user_id == current_user.id)
            )
        )
        excluded_ids = {id for (id,) in interacted.all()} | {current_user.id}

        # Базовый запрос
        query = (
            select(User)
            .options(
                selectinload(User.photo),
                selectinload(User.ratings_received)
            )
            .where(
                User.id.not_in(excluded_ids),
                User.photo != None
            )
        )

        # Применяем предпочтения
        if prefs:
            if prefs.preferred_gender and prefs.preferred_gender != "Любой":
                query = query.where(User.gender == prefs.preferred_gender)
            
            if prefs.min_age is not None:
                query = query.where(User.age >= prefs.min_age)
            if prefs.max_age is not None:
                query = query.where(User.age <= prefs.max_age)

            # Для рейтинга делаем отдельный подзапрос
            if prefs.min_rating is not None or prefs.max_rating is not None:
                avg_rating_subq = (
                    select(
                        Rating.to_user_id,
                        func.avg(Rating.score).label('avg_rating')
                    )
                    .group_by(Rating.to_user_id)
                    .subquery()
                )

                query = (
                    query.outerjoin(
                        avg_rating_subq,
                        avg_rating_subq.c.to_user_id == User.id
                    )
                )

                if prefs.min_rating is not None:
                    query = query.where(
                        func.coalesce(avg_rating_subq.c.avg_rating, 0.0) >= prefs.min_rating
                    )
                if prefs.max_rating is not None:
                    query = query.where(
                        func.coalesce(avg_rating_subq.c.avg_rating, 0.0) <= prefs.max_rating
                    )
        
        result = await session.execute(query)
        user = result.scalars().first()

        if user:
            full_name = " ".join(filter(None, [user.lastname, user.firstname, user.mname]))
            return {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "mname": user.mname,
                "full_name": full_name,
                "photo": user.photo.url,
                "bio": user.bio,
                "age": user.age,
                "gender": user.gender
            }

        return None


async def save_like(from_user_tg_id: int, to_user_id: int, is_like: bool = True):
    async with async_session() as session:
        from_user = await session.execute(
            select(User.id).where(User.tg_id == from_user_tg_id)
        )
        from_user_id = from_user.scalar_one()

        # Удаляем предыдущую реакцию если она есть
        await session.execute(
            delete(Like)
            .where(
                Like.from_user_id == from_user_id,
                Like.to_user_id == to_user_id
            )
        )

        # Добавляем новую реакцию (лайк или дизлайк)
        like = Like(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            is_like=is_like
        )
        session.add(like)
        
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise Exception(f"Ошибка сохранения реакции: {str(e)}")


async def save_rating(from_user_tg_id: int, to_user_id: int, score: int):
    async with async_session() as session:
        # Получаем ID отправителя
        from_user = await session.execute(
            select(User.id).where(User.tg_id == from_user_tg_id)
        )
        from_user_id = from_user.scalar_one()

        # Проверяем существующую оценку
        existing = await session.execute(
            select(Rating)
            .where(
                Rating.from_user_id == from_user_id,
                Rating.to_user_id == to_user_id
            )
        )
        existing = existing.scalar_one_or_none()

        if existing:
            # Обновляем существующую оценку
            existing.score = score
        else:
            # Создаем новую запись
            rating = Rating(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                score=score,
                comment=None  # Явно указываем NULL
            )
            session.add(rating)
        
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise Exception(f"Ошибка сохранения оценки: {str(e)}")

async def save_comment(from_user_tg_id: int, to_user_id: int, comment_text: str):
    async with async_session() as session:
        # Получаем ID отправителя
        from_user = await session.execute(
            select(User.id).where(User.tg_id == from_user_tg_id)
        )
        from_user_id = from_user.scalar_one()

        # Проверяем существующий комментарий
        existing = await session.execute(
            select(Rating)
            .where(
                Rating.from_user_id == from_user_id,
                Rating.to_user_id == to_user_id,
                Rating.comment.isnot(None)
            )
        )
        existing = existing.scalar_one_or_none()

        if existing:
            # Обновляем существующий комментарий
            existing.comment = comment_text
        else:
            # Создаем новую запись
            rating = Rating(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                score=0,  # Оценка по умолчанию
                comment=comment_text
            )
            session.add(rating)
        
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise Exception(f"Ошибка сохранения комментария: {str(e)}")


async def check_existing_comment(from_user_tg_id: int, to_user_id: int) -> bool:
    async with async_session() as session:
        from_user = await session.execute(
            select(User.id).where(User.tg_id == from_user_tg_id)
        )
        from_user_id = from_user.scalar_one()

        result = await session.execute(
            select(Rating)
            .where(
                Rating.from_user_id == from_user_id,
                Rating.to_user_id == to_user_id,
                Rating.comment.isnot(None)
            )
        )
        return result.scalar_one_or_none() is not None