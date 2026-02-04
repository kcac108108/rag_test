from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import settings


def get_chroma_persist_dir() -> Path:
    # 1) 설정값이 있으면 우선 사용
    if hasattr(settings, "chroma_persist_dir") and getattr(settings, "chroma_persist_dir"):
        return Path(getattr(settings, "chroma_persist_dir"))

    # 2) 없으면 프로젝트 루트 기준 기본값
    # paths.py가 있으면 그걸 쓰는 게 가장 안정적
    try:
        from app.utils.paths import project_root  # type: ignore
        return project_root() / "chroma_db"
    except Exception:
        return Path.cwd() / "chroma_db"


def reset_chroma_db() -> dict:
    persist_dir = get_chroma_persist_dir()
    existed = persist_dir.exists()

    if existed:
        shutil.rmtree(persist_dir, ignore_errors=True)

    # 폴더를 다시 만들어 두면 다음 인덱싱 때 안전
    persist_dir.mkdir(parents=True, exist_ok=True)

    return {
        "ok": True,
        "persist_dir": str(persist_dir),
        "deleted": existed,
        "message": "Chroma DB reset complete. Re-run /ingest/schema and /ingest/examples.",
    }
