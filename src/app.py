import asyncio
import logging
from bot import dp
from core.bot_instance import bot_instance as bot
from storage.redis_client import photo_cache
from storage.db import create_tables

logger = logging.getLogger(__name__)

async def main():
    logger.info("Запуск бота")
    try:
        logger.info("Создание таблиц в базе данных")
        await create_tables()
        
        logger.info("Запуск long-polling бота")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе бота: {str(e)}")
        raise
    finally:
        logger.info("Очистка ресурсов")
        try:
            await photo_cache.close()
            logger.debug("Соединение с Redis закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с Redis: {str(e)}")
        
        try:
            await dp.storage.close()
            logger.debug("Хранилище FSM закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии хранилища FSM: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Необработанное исключение: {str(e)}")
