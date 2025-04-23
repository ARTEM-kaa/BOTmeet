from aiogram import Dispatcher
from handlers.routers import user_router
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

dp = Dispatcher()
dp.include_router(user_router)
