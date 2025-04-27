import logging
from logging.handlers import RotatingFileHandler
from aiogram import Dispatcher
from handlers.routers import user_router
import sys
import os
from storage.redis import redis_storage

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('bot.log', maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)

logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)
logger.info("Starting bot initialization")

dp = Dispatcher(storage=redis_storage)
dp.include_router(user_router)

logger.info("Bot initialized successfully")
