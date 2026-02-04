from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.v1.router import api_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="Text-to-SQL RAG API")
app.include_router(api_router, prefix="/api/v1")

WEB_DIR = Path(__file__).resolve().parent / "web"

@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html")
