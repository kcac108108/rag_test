from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.router import api_router
from app.api.v1.std import router as std_router
from app.api.v1 import std_admin

from app.core.logging import setup_logging

# 🔹 web UI 라우터 추가
from app.webui.router import router as webui_router

setup_logging()

app = FastAPI(title="Text-to-SQL RAG API")

# ==============================
# API Routers
# ==============================
app.include_router(api_router, prefix="/api/v1")
app.include_router(std_router, prefix="/api/v1")
app.include_router(std_admin.router, prefix="/api/v1")

# ==============================
# Web UI Router
# ==============================
app.include_router(webui_router)

# ==============================
# Paths
# ==============================
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = BASE_DIR.parent / "static"

HOME_HTML = WEB_DIR / "home.html"
INDEX_HTML = WEB_DIR / "index.html"
AI_MAIN_HTML = WEB_DIR / "ai_main.html"

HOME_FILES_DIR = WEB_DIR / "home_files"

# ==============================
# Static Files
# ==============================
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if HOME_FILES_DIR.exists():
    app.mount("/home_files", StaticFiles(directory=HOME_FILES_DIR), name="home_files")

# ai_main.html 에서 쓰는 이미지 파일 접근용
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")

# favicon 404 방지
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_path = WEB_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return Response(status_code=204)

# ==============================
# Pages
# ==============================
@app.get("/", include_in_schema=False)
def root():
    if HOME_HTML.exists():
        return FileResponse(HOME_HTML)
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"message": "RAG API Server is running"}

@app.get("/home", include_in_schema=False)
def home():
    if HOME_HTML.exists():
        return FileResponse(HOME_HTML)
    return {"message": "home.html not found"}

@app.get("/ai", include_in_schema=False)
def ai_main():
    if AI_MAIN_HTML.exists():
        return FileResponse(AI_MAIN_HTML)
    return {"message": "ai_main.html not found"}

@app.get("/text-to-sql", include_in_schema=False)
def text_to_sql():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"message": "index.html not found"}