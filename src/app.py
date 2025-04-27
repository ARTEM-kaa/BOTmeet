import asyncio
from bot import dp
from core.bot_instance import bot_instance as bot
from storage.redis_client import photo_cache
from storage.db import create_tables

async def main():
    await create_tables()
    try:
        await dp.start_polling(bot)
    finally:
        await photo_cache.close()
        await dp.storage.close()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
