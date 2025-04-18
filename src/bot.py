from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from handlers.routers import user_router
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import settings

print(f"BOT_TOKEN from settings: {settings.BOT_TOKEN}")
print(f"BOT_TOKEN from os: {os.getenv('BOT_TOKEN')}")

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
dp.include_router(user_router)
