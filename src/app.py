import asyncio
from bot import dp
from core.bot_instance import bot_instance as bot
from storage.db import create_tables

async def main():
    await create_tables()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
