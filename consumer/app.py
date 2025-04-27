import asyncio
import msgpack
import logging
from aio_pika import connect_robust
from consumer.handlers.event_distribution import event_distribution
from config.settings import settings

logger = logging.getLogger(__name__)

async def main():
    logger.info("Запуск RabbitMQ consumer")
    try:
        logger.info(f"Подключение к RabbitMQ по URL: {settings.rebbitmq_url}")
        connection = await connect_robust(settings.rebbitmq_url)
        channel = await connection.channel()
        
        logger.info("Объявление очереди 'user_messages'")
        queue = await channel.declare_queue('user_messages', durable=True)
        
        logger.info("Начало обработки сообщений")
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        logger.debug(f"Получено новое сообщение: {message.body[:100]}...")
                        body = msgpack.unpackb(message.body)
                        logger.debug(f"Распакованное сообщение: {body}")
                        
                        await event_distribution(body)
                        logger.debug("Сообщение успешно обработано")
                        
                    except Exception as e:
                        logger.error(f"Ошибка обработки сообщения: {str(e)}", exc_info=True)
                        
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе consumer: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer остановлен пользователем")
    except Exception as e:
        logger.critical(f"Необработанное исключение: {str(e)}", exc_info=True)
