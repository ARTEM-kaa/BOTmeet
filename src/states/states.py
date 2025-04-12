from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_bio = State()
    waiting_for_photo = State()
