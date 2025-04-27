import asyncio
import msgpack
from aio_pika import connect_robust
from consumer.handlers.event_distribution import event_distribution
from config.settings import settings


async def main():
    connection = await connect_robust(settings.rebbitmq_url)
    channel = await connection.channel()
    
    queue = await channel.declare_queue('user_messages', durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    body = msgpack.unpackb(message.body)
                    await event_distribution(body)
                except Exception as e:
                    print(f"Error processing message: {e}")

if __name__ == "__main__":
    asyncio.run(main())
