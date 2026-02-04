from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.sql import router as sql_router
from app.api.v1.endpoints.ingest import router as ingest_router
from app.api.v1.endpoints.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(sql_router, prefix="/sql", tags=["sql"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
