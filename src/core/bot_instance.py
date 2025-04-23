from aiogram import Bot
from config.settings import settings
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

bot_instance = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
