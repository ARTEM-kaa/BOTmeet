from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from templates import keyboards, texts, constants
from states.states import RegistrationState
from storage.s3_yandex import upload_photo_to_s3
from storage.time_db_logic import create_user_profile


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
