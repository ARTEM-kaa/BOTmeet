from aiogram import F, Router
from aiogram.filters import CommandStart
import handlers.handlers as handlers
import templates.constants as constants
from states.states import RegistrationState

user_router = Router()

user_router.message.register(handlers.start, CommandStart())
user_router.callback_query.register(handlers.start_registration, F.data == constants.START_BUTTON_CALL)
user_router.message.register(handlers.get_full_name, RegistrationState.waiting_for_full_name)
user_router.message.register(handlers.get_age, RegistrationState.waiting_for_age)
user_router.callback_query.register(handlers.get_gender, RegistrationState.waiting_for_gender)
user_router.message.register(handlers.get_bio, RegistrationState.waiting_for_bio)
user_router.message.register(handlers.get_photo, RegistrationState.waiting_for_photo)
