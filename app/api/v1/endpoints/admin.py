from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.admin_service import reset_chroma_db

router = APIRouter()


@router.post("/reset-chroma")
def reset_chroma(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    if not settings.admin_reset_token:
        raise HTTPException(status_code=500, detail="ADMIN_RESET_TOKEN is not configured in .env")

    if x_admin_token != settings.admin_reset_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    return reset_chroma_db()
