from collections.abc import AsyncGenerator
from asyncpg import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import sys
import os
from config.settings import settings
from src.model.meta import Base
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_db_engine() -> AsyncEngine:
    logger.info("Создание асинхронного движка БД")
    return create_async_engine(
        settings.db_url,
        connect_args={"connection_class": Connection},
    )

def create_db_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    logger.info("Создание асинхронной сессии БД")
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

engine = create_db_engine()
async_session = create_db_session(engine)

async def create_tables():
    logger.info("Создание таблиц в БД")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    logger.debug("Получение сессии БД")
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка в сессии БД: {str(e)}")
            raise
