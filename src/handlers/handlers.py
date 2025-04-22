from aiogram.types import Message, CallbackQuery, Union
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload

from templates import keyboards, texts, constants
from states.states import RegistrationState, EditProfileState, PreferenceState, MeetingState
from storage.s3_yandex import upload_photo_to_s3
from storage.time_db_logic import create_user_profile, update_user_field, update_user_photo, update_user_preferences, get_next_profile, save_like, save_rating, save_comment, check_existing_comment
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
    if not msg.text:
        return await msg.answer(await texts.data_name_error())
    
    if any(char.isdigit() for char in msg.text):
        return await msg.answer(await texts.data_name_error_char())
    
    parts = msg.text.strip().split()
    if len(parts) != 3:
        return await msg.answer(await texts.ask_full_name_again())

    for part in parts:
        if not part.isalpha():
            return await msg.answer(await texts.data_name_error())

    await state.update_data(full_name=msg.text)
    await msg.answer(await texts.ask_age())
    await state.set_state(RegistrationState.waiting_for_age)


async def get_age(msg: Message, state: FSMContext):
    if not msg.text:
        return await msg.answer(await texts.ask_age_again())
    
    age = int(msg.text)
    
    if age < 10 or age > 110:
        return await msg.answer(await texts.age_length_error())

    await state.update_data(age=age)
    await msg.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(RegistrationState.waiting_for_gender)


async def get_gender(call: CallbackQuery, state: FSMContext):
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    await state.update_data(gender=gender)
    await call.message.delete()
    await call.message.answer(await texts.ask_bio())
    await state.set_state(RegistrationState.waiting_for_bio)


async def get_bio(msg: Message, state: FSMContext):
    if not msg.text:
        return await msg.answer(await texts.data_bio_error())
    
    if len(msg.text) > 500:
        return await msg.answer(await texts.bio_length_error())
    
    forbidden_chars = ["<", ">", "&", "'", "\""]
    if any(char in msg.text for char in forbidden_chars):
        return await msg.answer(await texts.prohibited_characters())

    await state.update_data(bio=msg.text)
    await msg.answer(await texts.ask_photo())
    await state.set_state(RegistrationState.waiting_for_photo)


async def get_photo(msg: Message, state: FSMContext):
    if not msg.photo:
        return await msg.answer(await texts.ask_photo_again())
    
    photo = msg.photo[-1]
    if photo.file_size > 10 * 1024 * 1024:
        return await msg.answer(await texts.error_photo())

    try:
        file = await msg.bot.get_file(photo.file_id)
        file_data = await msg.bot.download_file(file.file_path)
        
        if not file.file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return await msg.answer(await texts.error_photo_phormat())

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
        
    except Exception as e:
        await msg.answer("Произошла ошибка при обработке фото, попробуйте еще раз")


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
    try:
        async with async_session() as session:
            user_result = await session.execute(
                select(User.id).where(User.tg_id == call.from_user.id)
            )
            user_id = user_result.scalar_one()

            result = await session.execute(
                select(func.count())
                .select_from(Like)
                .where(
                    Like.to_user_id == user_id,
                    Like.is_like == True
                )
            )
            count = result.scalar()

        text = await texts.likes_count(count)
        await call.message.answer(text)
    except Exception as e:
        await call.message.answer(
            await texts.error_like(),
            reply_markup=await keyboards.back_to_menu_keyboard()
        )

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
        photo_url = user.photo.url if user.photo else "https://example.com/placeholder.jpg"

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




# КНОПКА НОМЕР 1 АНКЕТЫ:

async def start_meeting(event: Union[CallbackQuery, Message], state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        from_user_id = event.from_user.id
        answer_photo = event.message.answer_photo
        answer_text = event.message.answer
    else:
        from_user_id = event.from_user.id
        answer_photo = event.answer_photo
        answer_text = event.answer

    profile = await get_next_profile(current_tg_id=from_user_id)
    if not profile:
        return await answer_text(
            await texts.no_profiles_left(),
            reply_markup=await keyboards.back_to_menu_keyboard()
        )

    await state.set_state(MeetingState.viewing)
    await state.update_data(current_profile=profile)

    await answer_photo(
        photo=profile["photo"],
        caption=await texts.summary(profile),
        reply_markup=await keyboards.meeting_keyboard()
    )


async def like_profile(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    data = await state.get_data()
    profile = data["current_profile"]

    try:
        await save_like(
            from_user_tg_id=call.from_user.id, 
            to_user_id=profile["id"]
        )
    except Exception as e:
        return await call.message.answer(
            await texts.error_like(),
            reply_markup=await keyboards.back_to_menu_keyboard()
        )

    await call.message.answer(
        await texts.choose_stars(profile['full_name']),
        reply_markup=await keyboards.stars_keyboard()
    )
    await state.set_state(MeetingState.rating)


async def dislike_profile(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    data = await state.get_data()
    profile = data["current_profile"]

    try:
        await save_like(
            from_user_tg_id=call.from_user.id,
            to_user_id=profile["id"], 
            is_like=False
        )
        await call.message.answer(
            await texts.rating_prompt(profile['full_name']),
            reply_markup=await keyboards.stars_keyboard()
        )
        await state.set_state(MeetingState.rating)
    except Exception as e:
        await call.message.answer(
            await texts.error_dislike(),
            reply_markup=await keyboards.back_to_menu_keyboard()
        )



async def rate_profile(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profile = data["current_profile"]
    stars = int(call.data.split("_")[1])

    try:
        await save_rating(
            from_user_tg_id=call.from_user.id,
            to_user_id=profile["id"],
            score=stars
        )
        await call.answer(await texts.rate_sent())
    except Exception as e:
        await call.answer(await texts.error_rate())

    await start_meeting(call, state)


async def comment_profile(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    data = await state.get_data()
    profile = data["current_profile"]

    message = await call.message.answer(
        await texts.comment_prompt(profile['full_name']),
        reply_markup=await keyboards.back_to_profile_keyboard()
    )
    await state.update_data(comment_message_id=message.message_id)

    await state.set_state(MeetingState.comment)


async def show_profile_again(msg: Message, state: FSMContext, profile: dict):
    await msg.answer_photo(
        photo=profile["photo"],
        caption=await texts.summary(profile),
        reply_markup=await keyboards.meeting_keyboard()
    )
    await state.set_state(MeetingState.viewing)


async def get_comment(msg: Message, state: FSMContext):
    data = await state.get_data()
    profile = data["current_profile"]
    
    if 'comment_message_id' in data:
        await msg.bot.delete_message(
            chat_id=msg.chat.id,
            message_id=data['comment_message_id']
        )
    
    try:
        existing_comment = await check_existing_comment(
            from_user_tg_id=msg.from_user.id,
            to_user_id=profile["id"]
        )
        
        if existing_comment:
            await msg.answer(
                await texts.error_comment(),
            )
        else:
            await save_comment(
                from_user_tg_id=msg.from_user.id,
                to_user_id=profile["id"],
                comment_text=msg.text
            )
            await msg.answer(await texts.comment_sent())
            
        await show_profile_again(msg, state, profile)
        
    except Exception as e:
        await msg.answer(
            await texts.error_comment(),
            reply_markup=await keyboards.back_to_profile_keyboard()
        )


async def back_to_profile(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    data = await state.get_data()
    profile = data["current_profile"]

    await call.message.answer_photo(
        photo=profile["photo"],
        caption=await texts.summary(profile),
        reply_markup=await keyboards.meeting_keyboard()
    )
    await state.set_state(MeetingState.viewing)
