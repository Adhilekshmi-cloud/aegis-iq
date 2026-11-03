"""Database session and connection management for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import unquote, urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

# Ensure the parent directory exists for SQLite databases.
if DATABASE_URL.startswith("sqlite"):
    parsed_url = urlparse(DATABASE_URL)

    # SQLAlchemy SQLite URLs use the database path after the scheme.
    database_path = unquote(parsed_url.path)

    if database_path and database_path != "/:memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

logger.info("Database URL in use: %s", DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=(
        {"check_same_thread": False}
        if DATABASE_URL.startswith("sqlite")
        else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base model class for SQLAlchemy ORM."""


async def init_db() -> None:
    """Initialize database tables."""
    logger.info("Initializing database tables...")

    # Import models so they are registered with Base.metadata.
    from app.knowledge import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables initialized successfully.")


async def close_db() -> None:
    """Close the database connection pool."""
    logger.info("Disposing database engine connection pool...")
    await engine.dispose()
    logger.info("Database engine connection pool disposed.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Session transaction rolled back: %s", exc)
            raise