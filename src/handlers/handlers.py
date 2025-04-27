from aiogram.types import Message, CallbackQuery, Union, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import selectinload

from templates import keyboards, texts, constants
from states.states import RegistrationState, EditProfileState, PreferenceState, MeetingState
from storage.s3_yandex import upload_photo_to_s3, get_photo_with_cache
from storage.db import async_session
from sqlalchemy import select
from model.models import User, Preference
from src.storage import rabbit
import aio_pika
import msgpack
from config.settings import settings
from core.bot_instance import bot_instance
import logging


logger = logging.getLogger(__name__)

async def start(msg: Message):
    if not msg.from_user:
        logger.warning(f"Не удалось получить данные пользователя в сообщении: {msg}")
        await msg.answer('Не удалось получить данные пользователя.')
        return
    
    user_id = msg.from_user.id
    logger.info(f"Начало обработки команды /start для пользователя {user_id}")
    request_body = {'user_id': user_id, 'action': 'check_user_in_db'}
    
    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('user_check', aio_pika.ExchangeType.TOPIC, durable=True)

            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)

            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')

            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))

            await exchange.publish(aio_pika.Message(body=msgpack.packb(request_body)), routing_key='user_messages')

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break
        
        if response.get('exists'):
            logger.info(f"Пользователь {user_id} уже зарегистрирован")
            await msg.answer(
                await texts.already_registered(),
                reply_markup=await keyboards.main_menu_keyboard()
            )
        else:
            logger.info(f"Пользователь {user_id} новый, отправлено приветственное сообщение")
            await msg.answer(
                await texts.start_message(),
                reply_markup=await keyboards.start_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start для пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")


async def start_registration(call: CallbackQuery, state: FSMContext):
    logger.info(f"Начало регистрации для пользователя {call.from_user.id}")
    await call.message.delete()
    await call.message.answer(await texts.ask_full_name())
    await state.set_state(RegistrationState.waiting_for_full_name)


async def get_full_name(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил текст для имени")
        return await msg.answer(await texts.data_name_error())
    
    if any(char.isdigit() for char in msg.text):
        logger.warning(f"Пользователь {user_id} отправил имя с цифрами: {msg.text}")
        return await msg.answer(await texts.data_name_error_char())
    
    parts = msg.text.strip().split()
    if len(parts) != 3:
        logger.warning(f"Пользователь {user_id} отправил неполное имя: {msg.text}")
        return await msg.answer(await texts.ask_full_name_again())

    for part in parts:
        if not part.isalpha():
            logger.warning(f"Пользователь {user_id} отправил имя с недопустимыми символами: {msg.text}")
            return await msg.answer(await texts.data_name_error())

    logger.info(f"Пользователь {user_id} успешно ввел ФИО: {msg.text}")
    await state.update_data(full_name=msg.text)
    await msg.answer(await texts.ask_age())
    await state.set_state(RegistrationState.waiting_for_age)


async def get_age(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил возраст")
        return await msg.answer(await texts.ask_age_again())
    
    try:
        age = int(msg.text)
    except ValueError:
        logger.warning(f"Пользователь {user_id} отправил некорректный возраст: {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    if age < 10 or age > 110:
        logger.warning(f"Пользователь {user_id} отправил возраст вне допустимого диапазона: {age}")
        return await msg.answer(await texts.age_length_error())

    logger.info(f"Пользователь {user_id} успешно ввел возраст: {age}")
    await state.update_data(age=age)
    await msg.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(RegistrationState.waiting_for_gender)


async def get_gender(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    logger.info(f"Пользователь {user_id} выбрал пол: {gender}")
    await state.update_data(gender=gender)
    await call.message.delete()
    await call.message.answer(await texts.ask_bio())
    await state.set_state(RegistrationState.waiting_for_bio)


async def get_bio(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил био")
        return await msg.answer(await texts.data_bio_error())
    
    if len(msg.text) > 500:
        logger.warning(f"Пользователь {user_id} отправил слишком длинное био ({len(msg.text)} символов)")
        return await msg.answer(await texts.bio_length_error())
    
    forbidden_chars = ["<", ">", "&", "'", "\""]
    if any(char in msg.text for char in forbidden_chars):
        logger.warning(f"Пользователь {user_id} отправил био с запрещенными символами")
        return await msg.answer(await texts.prohibited_characters())

    logger.info(f"Пользователь {user_id} успешно ввел био")
    await state.update_data(bio=msg.text)
    await msg.answer(await texts.ask_photo())
    await state.set_state(RegistrationState.waiting_for_photo)


async def get_photo(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if hasattr(msg, 'media_group_id') and msg.media_group_id:
        logger.warning(f"Пользователь {user_id} отправил фото альбомом")
        return await msg.answer("⚠️ Пожалуйста, отправляйте фото по одному, а не альбомом")
    
    if not msg.photo:
        logger.warning(f"Пользователь {user_id} не отправил фото")
        return await msg.answer(await texts.ask_photo_again())
    
    photo = msg.photo[-1]
    if photo.file_size > 10 * 1024 * 1024:
        logger.warning(f"Пользователь {user_id} отправил слишком большое фото ({photo.file_size} байт)")
        return await msg.answer(await texts.error_photo())

    try:
        file = await msg.bot.get_file(photo.file_id)
        file_data = await msg.bot.download_file(file.file_path)
        
        if not file.file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.warning(f"Пользователь {user_id} отправил фото в недопустимом формате: {file.file_path}")
            return await msg.answer(await texts.error_photo_phormat())

        s3_url = await upload_photo_to_s3(
            file=file_data.read(),
            filename=file.file_path.split("/")[-1]
        )
        logger.info(f"Фото пользователя {user_id} успешно загружено в S3: {s3_url}")

        await state.update_data(photo=s3_url)
        user_data = await state.get_data()
        
        photo_data = await get_photo_with_cache(s3_url)

        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('user_actions', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))
            await user_queue.bind(exchange, routing_key='user_messages')

            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb({
                        'action': 'create_user_profile',
                        'user_id': user_id,
                        'tg_username': msg.from_user.username,
                        'user_data': user_data
                    })
                ),
                routing_key='user_messages'
            )
            logger.info(f"Данные пользователя {user_id} отправлены в очередь")

        await msg.answer(await texts.success())
        if photo_data:
            try:
                photo_file = BufferedInputFile(
                        file=photo_data,
                        filename="profile.jpg"
                    )
                await msg.answer_photo(
                    photo=photo_file,
                    caption=await texts.summary(user_data),
                    reply_markup=await keyboards.main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке фото пользователю {user_id}: {str(e)}")
                await msg.answer_photo(
                    photo=s3_url,
                    caption=await texts.summary(user_data),
                    reply_markup=await keyboards.main_menu_keyboard()
                )
        else:
            logger.warning(f"Не удалось загрузить фото из кеша для пользователя {user_id}")
            await msg.answer("⚠️ Не удалось загрузить фото. Попробуйте позже.")
            await msg.answer_photo(
                photo=s3_url,
                caption=await texts.summary(user_data),
                reply_markup=await keyboards.main_menu_keyboard()
            )
        logger.info(f"Регистрация пользователя {user_id} успешно завершена")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке фото пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка при обработке фото, попробуйте позже")


async def preferences(call: CallbackQuery):
    logger.info(f"Пользователь {call.from_user.id} открыл настройки предпочтений")
    await call.message.delete()
    await call.message.answer(
        await texts.set_preferences(),
        reply_markup=await keyboards.preferences_menu_keyboard()
    )
    
    
async def update_user_preferences_rabbit(user_tg_id: int, data: dict):
    logger.info(f"Обновление предпочтений пользователя {user_tg_id}: {data}")
    request_body = {
        'user_tg_id': user_tg_id,
        'data': data,
        'action': 'update_preferences'
    }
    
    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('preferences_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_tg_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_tg_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break
                    
            if response.get('user_tg_id') == user_tg_id:
                logger.info(f"Предпочтения пользователя {user_tg_id} успешно обновлены")
                return response
    except Exception as e:
        logger.error(f"Ошибка при обновлении предпочтений пользователя {user_tg_id}: {str(e)}")
        raise


async def send_profile_update(user_tg_id: int, update_data: dict, action_type: str = 'single') -> bool:
    logger.info(f"Отправка обновления профиля для пользователя {user_tg_id}: {update_data}")
    request_body = {
        'user_tg_id': user_tg_id,
        'data': update_data,
        'action': 'update_profile_field',
        'action_type': action_type
    }

    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('profile_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_tg_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_tg_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break
                    
            if response['status'] == 'success':
                logger.info(f"Профиль пользователя {user_tg_id} успешно обновлен")
                return True
            else:
                logger.warning(f"Не удалось обновить профиль пользователя {user_tg_id}")
                return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении профиля пользователя {user_tg_id}: {str(e)}")
        return False

# 1) Минимальный возраст
async def set_min_age(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал установку минимального возраста")
    await call.message.delete()
    await call.message.answer(await texts.min_age())
    await state.set_state(PreferenceState.waiting_for_min_age)


async def save_min_age(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text or not msg.text.isdigit():
        logger.warning(f"Пользователь {user_id} ввел некорректный минимальный возраст: {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    min_age = int(msg.text)
    
    if min_age < 10 or min_age > 110:
        logger.warning(f"Пользователь {user_id} ввел минимальный возраст вне диапазона: {min_age}")
        return await msg.answer(await texts.age_length_error())
    
    try:
        async with async_session() as session:
            user_result = await session.execute(
                select(User.id).where(User.tg_id == user_id)
            )
            user_id_db = user_result.scalar_one()

            prefs = await session.execute(
                select(Preference).where(Preference.user_id == user_id_db)
            )
            prefs = prefs.scalar_one()

            if hasattr(prefs, 'max_age') and min_age > prefs.max_age:
                logger.warning(f"Пользователь {user_id} ввел минимальный возраст больше максимального: {min_age} > {prefs.max_age}")
                return await msg.answer(await texts.min_age_error())

        await update_user_preferences_rabbit(user_id, {"min_age": min_age})
        logger.info(f"Пользователь {user_id} успешно установил минимальный возраст: {min_age}")
        await msg.answer(await texts.min_age_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении минимального возраста для пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")

# 2) Максимальный возраст
async def set_max_age(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал установку максимального возраста")
    await call.message.delete()
    await call.message.answer(await texts.max_age())
    await state.set_state(PreferenceState.waiting_for_max_age)


async def save_max_age(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text or not msg.text.isdigit():
        logger.warning(f"Пользователь {user_id} ввел некорректный максимальный возраст: {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    max_age = int(msg.text)
    
    if max_age < 10 or max_age > 110:
        logger.warning(f"Пользователь {user_id} ввел максимальный возраст вне диапазона: {max_age}")
        return await msg.answer(await texts.age_length_error())
    
    try:
        async with async_session() as session:
            user_result = await session.execute(
                select(User.id).where(User.tg_id == user_id)
            )
            user_id_db = user_result.scalar_one()
            
            prefs = await session.execute(
                select(Preference).where(Preference.user_id == user_id_db)
            )
            prefs = prefs.scalar_one()
            
            if hasattr(prefs, 'min_age') and max_age < prefs.min_age:
                logger.warning(f"Пользователь {user_id} ввел максимальный возраст меньше минимального: {max_age} < {prefs.min_age}")
                return await msg.answer(await texts.max_age_error())

        await update_user_preferences_rabbit(user_id, {"max_age": max_age})
        logger.info(f"Пользователь {user_id} успешно установил максимальный возраст: {max_age}")
        await msg.answer(await texts.max_age_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении максимального возраста для пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")

# 3) Минимальный рейтинг
async def set_min_rating(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал установку минимального рейтинга")
    await call.message.delete()
    await call.message.answer(await texts.min_rating())
    await state.set_state(PreferenceState.waiting_for_min_rating)


async def save_min_rating(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text or not msg.text.replace('.', '', 1).isdigit():
        logger.warning(f"Пользователь {user_id} ввел некорректный минимальный рейтинг: {msg.text}")
        return await msg.answer(await texts.ask_rating_again())
    
    min_rating = round(float(msg.text), 1)
    
    if min_rating < 0 or min_rating > 5:
        logger.warning(f"Пользователь {user_id} ввел минимальный рейтинг вне диапазона: {min_rating}")
        return await msg.answer(await texts.rating_range_error())
    
    try:
        async with async_session() as session:
            user_result = await session.execute(
                select(User.id).where(User.tg_id == user_id)
            )
            user_id_db = user_result.scalar_one()

            prefs = await session.execute(
                select(Preference).where(Preference.user_id == user_id_db)
            )
            prefs = prefs.scalar_one()

            if hasattr(prefs, 'max_rating') and min_rating > prefs.max_rating:
                logger.warning(f"Пользователь {user_id} ввел минимальный рейтинг больше максимального: {min_rating} > {prefs.max_rating}")
                return await msg.answer(await texts.min_rating_error())

        await update_user_preferences_rabbit(user_id, {"min_rating": min_rating})
        logger.info(f"Пользователь {user_id} успешно установил минимальный рейтинг: {min_rating}")
        await msg.answer(await texts.min_rating_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении минимального рейтинга для пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")

# 4) Максимальный рейтинг
async def set_max_rating(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал установку максимального рейтинга")
    await call.message.delete()
    await call.message.answer(await texts.max_rating())
    await state.set_state(PreferenceState.waiting_for_max_rating)


async def save_max_rating(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text or not msg.text.replace('.', '', 1).isdigit():
        logger.warning(f"Пользователь {user_id} ввел некорректный максимальный рейтинг: {msg.text}")
        return await msg.answer(await texts.ask_rating_again())
    
    max_rating = round(float(msg.text), 1)
    
    if max_rating < 0 or max_rating > 5:
        logger.warning(f"Пользователь {user_id} ввел максимальный рейтинг вне диапазона: {max_rating}")
        return await msg.answer(await texts.rating_range_error())
    
    try:
        async with async_session() as session:
            user_result = await session.execute(
                select(User.id).where(User.tg_id == user_id)
            )
            user_id_db = user_result.scalar_one()
            
            prefs = await session.execute(
                select(Preference).where(Preference.user_id == user_id_db)
            )
            prefs = prefs.scalar_one()
            
            if hasattr(prefs, 'min_rating') and max_rating < prefs.min_rating:
                logger.warning(f"Пользователь {user_id} ввел максимальный рейтинг меньше минимального: {max_rating} < {prefs.min_rating}")
                return await msg.answer(await texts.max_rating_error())

        await update_user_preferences_rabbit(user_id, {"max_rating": max_rating})
        logger.info(f"Пользователь {user_id} успешно установил максимальный рейтинг: {max_rating}")
        await msg.answer(await texts.max_rating_saved(), reply_markup=await keyboards.preferences_menu_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении максимального рейтинга для пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")


async def edit_profile(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} открыл редактирование профиля")
    await call.message.delete()
    await call.message.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


async def show_rating(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"Пользователь {user_id} запросил информацию о рейтинге")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Пользователь {user_id} не найден в базе при запросе рейтинга")
            return await call.message.answer(await texts.error_questionnaire())
        
        text = await texts.rating_info(
            user_rating=user.rating,
            like_count=user.like_count,
            dislike_count=user.dislike_count
        )
        
    await call.message.answer(text)


# 1) Редактировать фото
async def edit_photo(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал редактирование фото")
    await call.message.delete()
    await call.message.answer(await texts.edit_photo())
    await state.set_state(EditProfileState.waiting_for_new_photo)


# 2) Редактировать ФИО
async def edit_full_name(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал редактирование ФИО")
    await call.message.delete()
    await call.message.answer(await texts.edit_full_name())
    await state.set_state(EditProfileState.waiting_for_new_name)


# 3) Редактировать пол
async def edit_gender(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал редактирование пола")
    await call.message.delete()
    await call.message.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(EditProfileState.waiting_for_new_gender)


# 4) Редактировать возраст
async def edit_age(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал редактирование возраста")
    await call.message.delete()
    await call.message.answer(await texts.edit_age())
    await state.set_state(EditProfileState.waiting_for_new_age)


# 5) Редактировать био
async def edit_bio(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал редактирование био")
    await call.message.delete()
    await call.message.answer(await texts.edit_bio())
    await state.set_state(EditProfileState.waiting_for_new_bio)


# 7) Вернуться к 8 кнопкам
async def edit_back(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} вернулся в главное меню из редактирования")
    await call.message.delete()

    tg_id = call.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.photo)).where(User.tg_id == tg_id)
        )
        user = result.scalar_one()
        photo_url = user.photo.url

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
    user_id = msg.from_user.id
    if hasattr(msg, 'media_group_id') and msg.media_group_id:
        logger.warning(f"Пользователь {user_id} отправил фото альбомом")
        return await msg.answer("⚠️ Пожалуйста, отправляйте фото по одному, а не альбомом")

    if not msg.photo:
        logger.warning(f"Пользователь {user_id} не отправил фото")
        return await msg.answer(await texts.ask_photo_again())
    
    photo = msg.photo[-1]
    if photo.file_size > 10 * 1024 * 1024:
        logger.warning(f"Пользователь {user_id} отправил слишком большое фото ({photo.file_size} байт)")
        return await msg.answer(await texts.error_photo())

    try:
        file = await msg.bot.get_file(photo.file_id)
        file_data = await msg.bot.download_file(file.file_path)
        
        if not file.file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.warning(f"Пользователь {user_id} отправил фото в недопустимом формате: {file.file_path}")
            return await msg.answer(await texts.error_photo_phormat())

        request_body = {
            'user_tg_id': user_id,
            'file_data': file_data.read(),
            'filename': file.file_path.split("/")[-1],
            'action': 'update_photo'
        }
        
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('photo_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break
                    
            if response['status'] == 'success':
                logger.info(f"Фото пользователя {user_id} успешно обновлено")
                await msg.answer(await texts.updated_successfully())
                await msg.answer(
                    await texts.edit_profile_text(),
                    reply_markup=await keyboards.edit_profile_keyboard()
                )
                await state.clear()
            else:
                logger.error(f"Ошибка при обновлении фото пользователя {user_id}")
                await msg.answer("Ошибка при обработке фото")
    except Exception as e:
        logger.error(f"Ошибка при обработке нового фото пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")


# ФИО
async def get_new_full_name(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил текст для ФИО")
        return await msg.answer(await texts.data_name_error())
    
    if any(char.isdigit() for char in msg.text):
        logger.warning(f"Пользователь {user_id} отправил ФИО с цифрами: {msg.text}")
        return await msg.answer(await texts.data_name_error_char())
    
    parts = msg.text.strip().split()
    if len(parts) != 3:
        logger.warning(f"Пользователь {user_id} отправил неполное ФИО: {msg.text}")
        return await msg.answer(await texts.ask_full_name_again())

    for part in parts:
        if not part.isalpha():
            logger.warning(f"Пользователь {user_id} отправил ФИО с недопустимыми символами: {msg.text}")
            return await msg.answer(await texts.data_name_error())

    full_name = msg.text
    lastname, firstname, mname = full_name.split()
    update_data = {
        "firstname": firstname,
        "lastname": lastname,
        "mname": mname
    }
    success = await send_profile_update(user_id, update_data)

    if success:
        logger.info(f"ФИО пользователя {user_id} успешно обновлено")
        await msg.answer(await texts.updated_successfully())
        await msg.answer(
            await texts.edit_profile_text(),
            reply_markup=await keyboards.edit_profile_keyboard()
        )
        await state.clear()
    else:
        logger.error(f"Ошибка при обновлении ФИО пользователя {user_id}")
        await msg.answer("⚠️ Произошла ошибка при обновлении. Попробуйте позже.")


# Пол
async def get_new_gender(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    logger.info(f"Пользователь {user_id} изменил пол на {gender}")
    await send_profile_update(user_id, {"gender": gender})
    await call.message.delete()
    await call.message.answer(await texts.updated_successfully())
    await call.message.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# Возраст
async def get_new_age(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил возраст")
        return await msg.answer(await texts.ask_age_again())
    
    if not msg.text.isdigit():
        logger.warning(f"Пользователь {user_id} отправил некорректный возраст: {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    try:
        age = int(msg.text)
    except ValueError:
        logger.warning(f"Пользователь {user_id} отправил некорректный возраст: {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    if age < 10 or age > 110:
        logger.warning(f"Пользователь {user_id} отправил возраст вне диапазона: {age}")
        return await msg.answer(await texts.age_length_error())

    await send_profile_update(user_id, {"age": int(msg.text)})
    logger.info(f"Пользователь {user_id} изменил возраст на {age}")
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()


# Био
async def get_new_bio(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил био")
        return await msg.answer(await texts.data_bio_error())
    
    if len(msg.text) > 500:
        logger.warning(f"Пользователь {user_id} отправил слишком длинное био ({len(msg.text)} символов)")
        return await msg.answer(await texts.bio_length_error())
    
    forbidden_chars = ["<", ">", "&", "'", "\""]
    if any(char in msg.text for char in forbidden_chars):
        logger.warning(f"Пользователь {user_id} отправил био с запрещенными символами")
        return await msg.answer(await texts.prohibited_characters())

    await send_profile_update(user_id, {"bio": msg.text})
    logger.info(f"Пользователь {user_id} обновил био")
    await msg.answer(await texts.updated_successfully())
    await msg.answer(await texts.updated_successfully())
    await msg.answer(
        await texts.edit_profile_text(),
        reply_markup=await keyboards.edit_profile_keyboard()
    )
    await state.clear()
    
    
# 6) Изменить профиль целиком
async def edit_all(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {call.from_user.id} начал полное редактирование профиля")
    await call.message.delete()
    await call.message.answer(await texts.edit_full_name())
    await state.set_state(EditProfileState.editing_all_name)

# 1. ФИО
async def get_all_new_full_name(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил текст для ФИО (полное обновление)")
        return await msg.answer(await texts.data_name_error())
    
    if any(char.isdigit() for char in msg.text):
        logger.warning(f"Пользователь {user_id} отправил ФИО с цифрами (полное обновление): {msg.text}")
        return await msg.answer(await texts.data_name_error_char())
    
    parts = msg.text.strip().split()
    if len(parts) != 3:
        logger.warning(f"Пользователь {user_id} отправил неполное ФИО (полное обновление): {msg.text}")
        return await msg.answer(await texts.ask_full_name_again())

    for part in parts:
        if not part.isalpha():
            logger.warning(f"Пользователь {user_id} отправил ФИО с недопустимыми символами (полное обновление): {msg.text}")
            return await msg.answer(await texts.data_name_error())

    lastname, firstname, mname = msg.text.split()
    update_data = {
        "firstname": firstname,
        "lastname": lastname,
        "mname": mname
    }
    
    success = await send_profile_update(user_id, update_data, 'all')
    
    if success:
        logger.info(f"Пользователь {user_id} успешно обновил ФИО (полное обновление)")
        await msg.answer(await texts.edit_age())
        await state.set_state(EditProfileState.editing_all_age)
    else:
        logger.error(f"Ошибка при обновлении ФИО пользователя {user_id} (полное обновление)")
        await msg.answer("⚠️ Произошла ошибка при обновлении. Попробуйте позже.")

# 2. Возраст
async def get_all_new_age(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил возраст (полное обновление)")
        return await msg.answer(await texts.ask_age_again())
    
    if not msg.text.isdigit():
        logger.warning(f"Пользователь {user_id} отправил некорректный возраст (полное обновление): {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    try:
        age = int(msg.text)
    except ValueError:
        logger.warning(f"Пользователь {user_id} отправил некорректный возраст (полное обновление): {msg.text}")
        return await msg.answer(await texts.ask_age_again())
    
    if age < 10 or age > 110:
        logger.warning(f"Пользователь {user_id} отправил возраст вне диапазона (полное обновление): {age}")
        return await msg.answer(await texts.age_length_error())

    await send_profile_update(user_id, {"age": age}, 'all')
    logger.info(f"Пользователь {user_id} успешно обновил возраст (полное обновление): {age}")
    await msg.answer(await texts.ask_gender(), reply_markup=await keyboards.gender_keyboard())
    await state.set_state(EditProfileState.editing_all_gender)

# 3. Пол
async def get_all_new_gender(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    gender = "Мужской" if call.data == constants.MALE_CALL else "Женский"
    logger.info(f"Пользователь {user_id} выбрал пол (полное обновление): {gender}")
    await send_profile_update(user_id, {"gender": gender}, 'all')
    await call.message.delete()
    
    await call.message.answer(await texts.edit_bio())
    await state.set_state(EditProfileState.editing_all_bio)

# 4. Био
async def get_all_new_bio(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if not msg.text:
        logger.warning(f"Пользователь {user_id} не отправил био (полное обновление)")
        return await msg.answer(await texts.data_bio_error())
    
    if len(msg.text) > 500:
        logger.warning(f"Пользователь {user_id} отправил слишком длинное био (полное обновление): {len(msg.text)} символов")
        return await msg.answer(await texts.bio_length_error())
    
    forbidden_chars = ["<", ">", "&", "'", "\""]
    if any(char in msg.text for char in forbidden_chars):
        logger.warning(f"Пользователь {user_id} отправил био с запрещенными символами (полное обновление)")
        return await msg.answer(await texts.prohibited_characters())

    await send_profile_update(user_id, {"bio": msg.text}, 'all')
    logger.info(f"Пользователь {user_id} успешно обновил био (полное обновление)")
    await msg.answer(await texts.edit_photo())
    await state.set_state(EditProfileState.editing_all_photo)

# 5. Фото
async def get_all_new_photo(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    if hasattr(msg, 'media_group_id') and msg.media_group_id:
        logger.warning(f"Пользователь {user_id} отправил фото альбомом (полное обновление)")
        return await msg.answer("⚠️ Пожалуйста, отправляйте фото по одному, а не альбомом")

    if not msg.photo:
        logger.warning(f"Пользователь {user_id} не отправил фото (полное обновление)")
        return await msg.answer(await texts.ask_photo_again())
    
    photo = msg.photo[-1]
    if photo.file_size > 10 * 1024 * 1024:
        logger.warning(f"Пользователь {user_id} отправил слишком большое фото (полное обновление): {photo.file_size} байт")
        return await msg.answer(await texts.error_photo())

    try:
        file = await msg.bot.get_file(photo.file_id)
        file_data = await msg.bot.download_file(file.file_path)
        
        if not file.file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.warning(f"Пользователь {user_id} отправил фото в недопустимом формате (полное обновление): {file.file_path}")
            return await msg.answer(await texts.error_photo_phormat())

        request_body = {
            'user_tg_id': user_id,
            'file_data': file_data.read(),
            'filename': file.file_path.split("/")[-1],
            'action': 'update_photo',
            'full_update': True
        }
        
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('photo_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break

            if response['status'] == 'success':
                logger.info(f"Фото пользователя {user_id} успешно обновлено (полное обновление)")
                await full_profile_update(msg, response['photo_url'])
                await state.clear()
            else:
                logger.error(f"Ошибка при обновлении фото пользователя {user_id} (полное обновление)")
                await msg.answer("Ошибка при обработке фото")
    except Exception as e:
        logger.error(f"Ошибка при обработке фото пользователя {user_id} (полное обновление): {str(e)}")
        await msg.answer("Произошла ошибка, попробуйте позже")

async def full_profile_update(msg: Message, photo_url: str):
    user_id = msg.from_user.id
    logger.info(f"Завершение полного обновления профиля для пользователя {user_id}")
    try:
        tg_id = msg.from_user.id
        async with async_session() as session:
            result = await session.execute(select(User).options(selectinload(User.photo)).where(User.tg_id == tg_id))
            user = result.scalar_one()
            
            user_data = {
                "full_name": f"{user.lastname} {user.firstname} {user.mname}",
                "age": user.age,
                "gender": user.gender,
                "bio": user.bio,
                "photo": photo_url
            }

        await msg.answer(await texts.profile_updated_completely())
        await msg.bot.send_photo(
            chat_id=msg.chat.id,
            photo=user_data["photo"],
            caption=await texts.summary(user_data),
            reply_markup=await keyboards.main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при завершении полного обновления профиля пользователя {user_id}: {str(e)}")
        await msg.answer("Произошла ошибка при отображении профиля")

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

    logger.info(f"Начало встречи для пользователя {from_user_id}")

    state_data = await state.get_data()
    commented_but_not_rated = state_data.get('commented_but_not_rated')

    request_body = {
        'current_tg_id': from_user_id,
        'commented_but_not_rated': commented_but_not_rated,
        'action': 'get_next_profile'
    }
    
    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('meeting_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=from_user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=from_user_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break 
                
        if response['status'] == 'success':
            profile = response['profile']
            logger.info(f"Пользователю {from_user_id} показан профиль {profile.get('id')}")
            await state.set_state(MeetingState.viewing)
            await state.update_data(current_profile=profile)
            
            await answer_photo(
                photo=profile["photo"],
                caption=await texts.summary(profile),
                reply_markup=await keyboards.meeting_keyboard()
            )
        else:
            logger.info(f"Для пользователя {from_user_id} не найдено подходящих профилей")
            await answer_text(
                await texts.no_profiles_left(),
                reply_markup=await keyboards.back_to_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при старте встречи для пользователя {from_user_id}: {str(e)}")
        await answer_text("Произошла ошибка, попробуйте позже")


async def like_profile(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось убрать клавиатуру у сообщения для пользователя {user_id}: {str(e)}")
    
    data = await state.get_data()
    profile = data.get("current_profile")
    if not profile:
        logger.warning(f"Пользователь {user_id} пытался лайкнуть несуществующий профиль")
        await call.answer(await texts.error_questionnaire(), show_alert=True)
        return

    logger.info(f"Пользователь {user_id} лайкает профиль {profile.get('id')}")

    request_body = {
        'from_user_tg_id': user_id,
        'to_user_id': profile["id"],
        'is_like': True,
        'action': 'process_like'
    }
    
    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('likes_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break

        if response['status'] == 'success':
            logger.info(f"Лайк пользователя {user_id} для профиля {profile.get('id')} успешно сохранен")
            await call.answer(await texts.saving_like())
            if response.get('match'):
                matched_user = response['matched_user']
                logger.info(f"Обнаружен мэтч между пользователями {user_id} и {matched_user.get('tg_id')}")
                message_text = await texts.match_notification(matched_user.get('tg_username'))
                await call.message.answer(message_text)
                from_user_data = response['from_user_data']
                second_user_username = from_user_data.get('tg_username')
                
                message = await texts.match_notification(second_user_username)
                await bot_instance.send_message(
                    chat_id=matched_user['tg_id'],
                    text=message
                )
            await start_meeting(call, state)
        else:
            logger.error(f"Ошибка при сохранении лайка от пользователя {user_id} для профиля {profile.get('id')}")
            await call.answer(await texts.error_saving_like(), show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке лайка от пользователя {user_id}: {str(e)}")
        await call.answer("Произошла ошибка, попробуйте позже", show_alert=True)


async def dislike_profile(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось убрать клавиатуру у сообщения для пользователя {user_id}: {str(e)}")

    data = await state.get_data()
    profile = data.get("current_profile")
    if not profile:
        logger.warning(f"Пользователь {user_id} пытался дизлайкнуть несуществующий профиль")
        await call.answer(await texts.error_questionnaire(), show_alert=True)
        return

    logger.info(f"Пользователь {user_id} дизлайкает профиль {profile.get('id')}")

    request_body = {
        'from_user_tg_id': user_id,
        'to_user_id': profile["id"],
        'is_like': False,
        'action': 'process_dislike'
    }
    
    try:
        async with rabbit.channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange('likes_updates', aio_pika.ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)
            user_queue = await channel.declare_queue('user_messages', durable=True)

            await user_queue.bind(exchange, 'user_messages')
            
            await queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))
            
            await exchange.publish(
                aio_pika.Message(
                    body=msgpack.packb(request_body),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='user_messages'
            )
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = msgpack.unpackb(message.body)
                        break

        if response['status'] == 'success':
            logger.info(f"Дизлайк пользователя {user_id} для профиля {profile.get('id')} успешно сохранен")
            await call.answer(await texts.saving_dislike())
            await start_meeting(call, state)
        else:
            logger.error(f"Ошибка при сохранении дизлайка от пользователя {user_id} для профиля {profile.get('id')}")
            await call.answer(await texts.error_saving_dislike(), show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке дизлайка от пользователя {user_id}: {str(e)}")
        await call.answer("Произошла ошибка, попробуйте позже", show_alert=True)


async def show_profile_again(msg: Message, state: FSMContext, profile: dict):
    user_id = msg.from_user.id
    logger.info(f"Повторный показ профиля {profile.get('id')} для пользователя {user_id}")
    await msg.answer_photo(
        photo=profile["photo"],
        caption=await texts.summary(profile),
        reply_markup=await keyboards.meeting_keyboard()
    )
    await state.set_state(MeetingState.viewing)
