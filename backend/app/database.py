import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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

    attempts = max(1, settings.db_init_max_retries)
    base_delay = max(0.5, float(settings.db_init_retry_interval_seconds))

    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database schema ready.")
            return
        except Exception as exc:  # pragma: no cover - best effort logging branch
            if attempt == attempts:
                logger.exception("Database initialization failed after %s attempts.", attempts)
                raise

            delay = base_delay * attempt
            logger.warning(
                "Database init attempt %s/%s failed: %s. Retrying in %.1fs...",
                attempt,
                attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

