from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["web-ui"])

# ✅ 템플릿 폴더를 "프로젝트 루트/templates"로 고정 (uvicorn 실행 위치에 영향 안 받게)
BASE_DIR = Path(__file__).resolve().parents[2]  # .../rag_test
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/ui/claimant", response_class=HTMLResponse)
def ui_claimant(request: Request):
    return templates.TemplateResponse(
        "claimant.html",
        {"request": request, "title": "신고인 - 표준품명 추천"},
    )


@router.get("/ui/admin", response_class=HTMLResponse)
def ui_admin(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "title": "관리자 - 승인/거절"},
    )