from aiogram import Dispatcher
from handlers.routers import user_router
import sys
import os
from storage.redis import redis_storage

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

dp = Dispatcher(storage=redis_storage)
dp.include_router(user_router)