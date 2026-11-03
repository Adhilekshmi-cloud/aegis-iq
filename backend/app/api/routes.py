"""Main API route registration for Aegis Knowledge System."""

from fastapi import APIRouter

from app.api.evaluation import router as evaluation_router
from app.api.ingest import router as ingest_router
from app.api.knowledge import router as knowledge_router
from app.api.query import router as query_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(ingest_router)
api_router.include_router(query_router)
api_router.include_router(knowledge_router)
api_router.include_router(evaluation_router)
