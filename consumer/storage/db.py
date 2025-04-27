from collections.abc import AsyncGenerator
from asyncpg import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import sys
import os
import logging
from config.settings import settings
from src.model.meta import Base

logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_db_engine() -> AsyncEngine:
    logger.info("Creating database engine with URL: %s", settings.db_url)
    return create_async_engine(
        settings.db_url,
        connect_args={"connection_class": Connection},
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )

def create_db_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    logger.info("Creating async session factory")
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
        future=True
    )

engine = create_db_engine()
async_session = create_db_session(engine)

async def create_tables():
    logger.info("Creating database tables")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully")
    except Exception as e:
        logger.error("Failed to create tables: %s", str(e))
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    logger.debug("Creating new database session")
    session = async_session()
    try:
        yield session
        await session.commit()
        logger.debug("Session committed successfully")
    except Exception as e:
        await session.rollback()
        logger.error("Session rollback due to error: %s", str(e))
        raise
