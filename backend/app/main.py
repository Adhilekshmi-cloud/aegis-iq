"""FastAPI main application entrypoint for Aegis Knowledge System."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import settings
from app.database import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    logger.info("Starting up %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database during startup: %s", exc)
        raise

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)
    try:
        await close_db()
        logger.info("Database connection closed cleanly.")
    except Exception as exc:
        logger.error("Error closing database during shutdown: %s", exc)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend core engine for technical document extraction, entity resolution, and grounded knowledge retrieval.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)


@app.get("/", tags=["System"])
async def root() -> Dict[str, str]:
    """Root endpoint returning system metadata and available documentation links."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint to verify system operability."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
