from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_bio = State()
    waiting_for_photo = State()


class EditProfileState(StatesGroup):
    waiting_for_new_photo = State()
    waiting_for_new_name = State()
    waiting_for_new_gender = State()
    waiting_for_new_age = State()
    waiting_for_new_bio = State()
    editing_all_photo = State()
    editing_all_name = State()
    editing_all_gender = State()
    editing_all_age = State()
    editing_all_bio = State()


class PreferenceState(StatesGroup):
    waiting_for_min_age = State()
    waiting_for_max_age = State()
    waiting_for_min_rating = State()
    waiting_for_max_rating = State()


class MeetingState(StatesGroup):
    viewing = State()
    commented_not_rated = State()
