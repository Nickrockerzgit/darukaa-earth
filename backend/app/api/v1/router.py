"""Aggregates every v1 endpoint module into a single router."""

from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, projects, sites

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(sites.router)
api_router.include_router(analytics.router)

__all__ = ["api_router"]
