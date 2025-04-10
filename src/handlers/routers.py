from aiogram import F, Router
from aiogram.filters import CommandStart

import handlers.handlers as handlers
import templates.constants as constants

user_router = Router()

user_router.message.register(handlers.start, CommandStart())
