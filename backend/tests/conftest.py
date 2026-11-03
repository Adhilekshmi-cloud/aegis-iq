"""Pytest configuration and async fixtures for Aegis Knowledge System."""

from typing import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.knowledge.models import *  # noqa: F401, F403
from app.api.routes import api_router

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _make_test_app() -> FastAPI:
    """Build a lightweight FastAPI test instance with no real DB lifespan."""

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield  # no init_db, no close_db

    test_app = FastAPI(lifespan=_noop_lifespan)
    from fastapi.middleware.cors import CORSMiddleware
    test_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    test_app.include_router(api_router)

    @test_app.get("/")
    async def root():
        return {"name": "Aegis Knowledge System", "version": "1.0.0", "status": "online", "docs_url": "/docs"}

    @test_app.get("/health")
    async def health():
        return {"status": "healthy", "app": "Aegis Knowledge System", "version": "1.0.0", "database": "connected"}

    return test_app


# Shared test FastAPI app (no real DB)
_test_app = _make_test_app()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Fresh in-memory SQLite engine per test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Fresh session from the in-memory engine."""
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to the in-memory test database."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    _test_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    _test_app.dependency_overrides.clear()
