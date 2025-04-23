from model.models import User, Photo, Preference, Like  # Убрали Rating
from storage.db import async_session
from datetime import datetime
from sqlalchemy import select, update, func, delete, and_
from sqlalchemy.exc import IntegrityError
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload


async def is_user_registered(tg_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        return result.scalar_one_or_none() is not None


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
                rating=2.5,  # Стартовый рейтинг 2.5
                like_count=0,
                dislike_count=0,
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


async def update_user_rating(to_user_id: int):
    async with async_session() as session:
        # Получаем количество лайков и дизлайков
        likes = await session.execute(
            select(func.count()).where(
                Like.to_user_id == to_user_id,
                Like.is_like == True
            )
        )
        like_count = likes.scalar() or 0

        dislikes = await session.execute(
            select(func.count()).where(
                Like.to_user_id == to_user_id,
                Like.is_like == False
            )
        )
        dislike_count = dislikes.scalar() or 0

        # Рассчитываем новый рейтинг (формула может быть изменена)
        base_rating = 2.5
        like_weight = 0.1
        dislike_weight = 0.15
        
        new_rating = base_rating + (like_count * like_weight) - (dislike_count * dislike_weight)
        new_rating = max(0.0, min(5.0, new_rating))  # Ограничиваем диапазон

        # Обновляем данные пользователя
        await session.execute(
            update(User)
            .where(User.id == to_user_id)
            .values(
                rating=new_rating,
                like_count=like_count,
                dislike_count=dislike_count
            )
        )
        await session.commit()


async def get_next_profile(current_tg_id: int, state: FSMContext = None):
    async with async_session() as session:
        # Проверяем есть ли неоцененная анкета с комментарием
        if state:
            data = await state.get_data()
            if 'commented_but_not_rated' in data:
                profile = data['commented_but_not_rated']
                return profile

        # Получаем текущего пользователя
        user_result = await session.execute(
            select(User).where(User.tg_id == current_tg_id))
        current_user = user_result.scalar_one_or_none()
        if not current_user:
            return None

        # Получаем ID пользователей, с которыми уже взаимодействовали
        interacted = await session.execute(
            select(Like.to_user_id).where(Like.from_user_id == current_user.id)
        )
        excluded_ids = {id for (id,) in interacted.all()} | {current_user.id}

        # Получаем предпочтения
        pref_result = await session.execute(
            select(Preference).where(Preference.user_id == current_user.id)
        )
        prefs = pref_result.scalar_one_or_none()

        # Базовый запрос
        query = (
            select(User)
            .options(selectinload(User.photo))
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

            # Фильтрация по рейтингу (теперь используем поле rating из User)
            if prefs.min_rating is not None:
                query = query.where(User.rating >= prefs.min_rating)
            if prefs.max_rating is not None:
                query = query.where(User.rating <= prefs.max_rating)
        
        result = await session.execute(query.order_by(func.random()))
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
                "gender": user.gender,
                "rating": float(user.rating)  # Явное преобразование для Decimal
            }

        return None


async def save_like(from_user_tg_id: int, to_user_id: int, is_like: bool = True):
    async with async_session() as session:
        # Получаем ID отправителя
        from_user = await session.execute(
            select(User.id).where(User.tg_id == from_user_tg_id))
        from_user_id = from_user.scalar_one()

        # Удаляем предыдущую реакцию если она есть
        await session.execute(
            delete(Like)
            .where(
                Like.from_user_id == from_user_id,
                Like.to_user_id == to_user_id
            )
        )

        # Добавляем новую реакцию
        like = Like(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            is_like=is_like,
            liked_at=datetime.utcnow()
        )
        session.add(like)
        
        try:
            await session.commit()
            # Обновляем рейтинг получателя
            await update_user_rating(to_user_id)
        except Exception as e:
            await session.rollback()
            raise Exception(f"Ошибка сохранения реакции: {str(e)}")


# async def save_comment(from_user_tg_id: int, to_user_id: int, comment_text: str):
#     """Теперь комментарии сохраняются в отдельной таблице (если нужно)"""
#     # В новой системе можно либо:
#     # 1. Сохранять комментарии в Like (добавить поле comment)
#     # 2. Создать отдельную таблицу для комментариев
#     # 3. Пропустить эту функцию, если комментарии не нужны
    
#     # Пример реализации через Like:
#     async with async_session() as session:
#         from_user = await session.execute(select(User.id).where(User.tg_id == from_user_tg_id))
#         from_user_id = from_user.scalar_one()

#         # Обновляем существующий лайк/дизлайк или создаем новый
#         existing = await session.execute(
#             select(Like)
#             .where(
#                 Like.from_user_id == from_user_id,
#                 Like.to_user_id == to_user_id
#             )
#         )
#         like = existing.scalar_one_or_none()

#         if like:
#             like.comment = comment_text  # Добавляем поле comment в модель Like
#         else:
#             like = Like(
#                 from_user_id=from_user_id,
#                 to_user_id=to_user_id,
#                 is_like=True,  # По умолчанию считаем с комментарием как лайк
#                 comment=comment_text,
#                 liked_at=datetime.utcnow()
#             )
#             session.add(like)
        
#         try:
#             await session.commit()
#         except Exception as e:
#             await session.rollback()
#             raise Exception(f"Ошибка сохранения комментария: {str(e)}")


# async def check_existing_comment(from_user_tg_id: int, to_user_id: int) -> bool:
#     async with async_session() as session:
#         from_user = await session.execute(
#             select(User.id).where(User.tg_id == from_user_tg_id))
#         from_user_id = from_user.scalar_one()

#         result = await session.execute(
#             select(Like)
#             .where(
#                 Like.from_user_id == from_user_id,
#                 Like.to_user_id == to_user_id,
#                 Like.comment.isnot(None)  # Предполагаем добавление поля comment в Like
#             )
#         )
#         return result.scalar_one_or_none() is not None