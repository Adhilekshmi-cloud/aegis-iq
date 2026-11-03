"""Database session and connection management for Aegis Knowledge System."""

from pathlib import Path

from sqlalchemy import MetaData
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


# Shared SQLAlchemy base used by all models.
class Base(DeclarativeBase):
    metadata = MetaData()


# Parse the URL safely. Do not manually strip the SQLite URL prefix.
database_url = make_url(settings.DATABASE_URL)

# Create the parent directory for file-based SQLite databases.
if database_url.get_backend_name() == "sqlite":
    database_path = database_url.database

    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """Create all tables registered with Base."""
    # Import model modules so their tables are registered on Base.metadata.
    import app.knowledge.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the database connection pool."""
    await engine.dispose()


async def get_db():
    """Yield an async database session for a request and commit automatically."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
