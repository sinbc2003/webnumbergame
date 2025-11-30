from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    # Import models for SQLModel metadata registration
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

