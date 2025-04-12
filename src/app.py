import asyncio
from bot import bot, dp
from storage.db import create_tables

async def main():
    await create_tables()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
