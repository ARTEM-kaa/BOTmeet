from collections.abc import AsyncGenerator
from asyncpg import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import sys
import os
from config.settings import settings
from src.model.meta import Base

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_db_engine() -> AsyncEngine:
    return create_async_engine(
        settings.db_url,
        connect_args={"connection_class": Connection},
    )

def create_db_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

engine = create_db_engine()
async_session = create_db_session(engine)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
