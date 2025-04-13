from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload

from templates import keyboards, texts, constants
from states.states import RegistrationState, EditProfileState, PreferenceState
from storage.s3_yandex import upload_photo_to_s3
from storage.time_db_logic import create_user_profile, update_user_field, update_user_photo, update_user_preferences
from storage.db import async_session
from sqlalchemy import select, func
from model.models import Like, Rating, User


async def start(msg: Message):
    await msg.answer(
        await texts.start_message(),
        reply_markup=await keyboards.start_keyboard()
    )


async def start_registration(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.ask_full_name())
    await state.set_state(RegistrationState.waiting_for_full_name)


async def get_full_name(msg: Message, state: FSMContext):
    parts = msg.text.strip().split()
    if len(parts) != 3:
        return await msg.answer(await texts.ask_full_name_again())

    await state.update_data(full_name=msg.text)
    await msg.answer(await texts.ask_age())
    await state.set_state(RegistrationState.waiting_for_age)


async def get_age(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        return await msg.answer(await texts.ask_age_again())

    await state.update_data(age=msg.text)
    await msg.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(RegistrationState.waiting_for_gender)


async def get_gender(call: CallbackQuery, state: FSMContext):
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    await state.update_data(gender=gender)
    await call.message.delete()
    await call.message.answer(await texts.ask_bio())
    await state.set_state(RegistrationState.waiting_for_bio)


async def get_bio(msg: Message, state: FSMContext):
    await state.update_data(bio=msg.text)
    await msg.answer(await texts.ask_photo())
    await state.set_state(RegistrationState.waiting_for_photo)


async def get_photo(msg: Message, state: FSMContext):
    if not msg.photo:
        return await msg.answer(await texts.ask_photo_again())

    photo = msg.photo[-1]
    file = await msg.bot.get_file(photo.file_id)
    file_data = await msg.bot.download_file(file.file_path)

    s3_url = await upload_photo_to_s3(
        file=file_data.read(),
        filename=file.file_path.split("/")[-1]
    )

    await state.update_data(photo=s3_url)
    user_data = await state.get_data()

    await create_user_profile(user_id=msg.from_user.id, data=user_data)

    await msg.answer(await texts.success())
    await msg.answer_photo(
        photo=user_data["photo"],
        caption=await texts.summary(user_data),
        reply_markup=await keyboards.main_menu_keyboard()
    )
    await state.clear()


async def preferences(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        await texts.set_preferences(),
        reply_markup=await keyboards.preferences_menu_keyboard()
    )


# 1) Минимальный возраст
async def set_min_age(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.min_age())
    await state.set_state(PreferenceState.waiting_for_min_age)


async def save_min_age(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        return await msg.answer(await texts.ask_age_again())
    
    await update_user_preferences(msg.from_user.id, {"min_age": int(msg.text)})
    await msg.answer(await texts.min_age_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
    await state.clear()


# 2) Максимальный возраст
async def set_max_age(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.max_age())
    await state.set_state(PreferenceState.waiting_for_max_age)


async def save_max_age(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        return await msg.answer(await texts.ask_age_again())
    
    await update_user_preferences(msg.from_user.id, {"max_age": int(msg.text)})
    await msg.answer(await texts.max_age_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
    await state.clear()


# 3) Минимальный рейтинг
async def set_min_rating(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.min_rating())
    await state.set_state(PreferenceState.waiting_for_min_rating)


async def save_min_rating(msg: Message, state: FSMContext):
    if not msg.text.replace('.', '', 1).isdigit():
        return await msg.answer(await texts.ask_rating_again())
    
    await update_user_preferences(msg.from_user.id, {"min_rating": float(msg.text)})
    await msg.answer(await texts.min_rating_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
    await state.clear()


# 4) Максимальный рейтинг
async def set_max_rating(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.max_rating())
    await state.set_state(PreferenceState.waiting_for_max_rating)


async def save_max_rating(msg: Message, state: FSMContext):
    if not msg.text.replace('.', '', 1).isdigit():
        return await msg.answer(await texts.ask_rating_again())
    
    await update_user_preferences(msg.from_user.id, {"max_rating": float(msg.text)})
    await msg.answer(await texts.max_rating_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
    await state.clear()


async def edit_profile(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


async def show_likes_count(call: CallbackQuery):
    user_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(Like).where(Like.to_user_id == user_id)
        )
        count = result.scalar()

    text = await texts.likes_count(count)
    await call.message.answer(text)


async def show_rating(call: CallbackQuery):
    user_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(
                func.coalesce(func.avg(Rating.score), 0),
                func.count(Rating.score)
            ).where(Rating.to_user_id == user_id)
        )
        avg_rating, rating_count = result.one()

    text = await texts.rating_info(avg_rating, rating_count)
    await call.message.answer(text)

# 1) Редактировать фото
async def edit_photo(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.edit_photo())
    await state.set_state(EditProfileState.waiting_for_new_photo)


# 2) Редактировать ФИО
async def edit_full_name(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.edit_full_name())
    await state.set_state(EditProfileState.waiting_for_new_name)


# 3) Редактировать пол
async def edit_gender(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(EditProfileState.waiting_for_new_gender)


# 4) Редактировать возраст
async def edit_age(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.edit_age())
    await state.set_state(EditProfileState.waiting_for_new_age)


# 5) Редактировать био
async def edit_bio(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(await texts.edit_bio())
    await state.set_state(EditProfileState.waiting_for_new_bio)


# 6) Изменить профиль целиком
async def edit_all(call: CallbackQuery, state: FSMContext):
    await start_registration(call, state)


# 7) Вернуться к 8 кнопкам
async def edit_back(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    tg_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.photo)).where(User.tg_id == tg_id)
        )
        user = result.scalar_one()
        photo_url = user.photo.url if user.photo else "https://example.com/placeholder.jpg"  # На случай, если нет фото

        user_data = {
            "full_name": f"{user.lastname} {user.firstname} {user.mname}",
            "age": user.age,
            "gender": user.gender,
            "bio": user.bio,
            "photo": photo_url
        }

    await call.message.answer_photo(
        photo=user_data["photo"],
        caption=await texts.summary(user_data),
        reply_markup=await keyboards.main_menu_keyboard()
    )


# Фото
async def get_new_photo(msg: Message, state: FSMContext):
    if not msg.photo:
        return await msg.answer(await texts.ask_photo_again())

    photo = msg.photo[-1]
    file = await msg.bot.get_file(photo.file_id)
    file_data = await msg.bot.download_file(file.file_path)

    s3_url = await upload_photo_to_s3(file=file_data.read(), filename=file.file_path.split("/")[-1])
    await update_user_photo(user_id=msg.from_user.id, url=s3_url)
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# ФИО
async def get_new_full_name(msg: Message, state: FSMContext):
    parts = msg.text.strip().split()
    if len(parts) != 3:
        return await msg.answer(await texts.ask_full_name_again())

    full_name = msg.text
    lastname, firstname, mname = full_name.split()
    await update_user_field(msg.from_user.id, {
        "firstname": firstname,
        "lastname": lastname,
        "mname": mname
    })
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# Пол
async def get_new_gender(call: CallbackQuery, state: FSMContext):
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    await update_user_field(call.from_user.id, {"gender": gender})
    await call.message.delete()
    await call.message.answer(await texts.updated_successfully())
    await call.message.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# Возраст
async def get_new_age(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        return await msg.answer(await texts.ask_age_again())

    await update_user_field(msg.from_user.id, {"age": int(msg.text)})
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# Био
async def get_new_bio(msg: Message, state: FSMContext):
    await update_user_field(msg.from_user.id, {"bio": msg.text})
    await msg.answer(await texts.updated_successfully())
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()
