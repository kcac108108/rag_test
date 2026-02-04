from typing import Any, Dict, List
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.core.config import settings

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise ValueError("DATABASE_URL is empty. Set it in .env")
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine

def execute_sql(sql: str, row_limit: int) -> List[Dict[str, Any]]:
    engine = get_engine()
    rows: List[Dict[str, Any]] = []
    with engine.connect() as conn:
        # Postgres statement timeout (best-effort)
        try:
            conn.execute(text(f"SET LOCAL statement_timeout = {int(settings.statement_timeout_sec*1000)}"))
        except Exception:
            pass

        result = conn.execute(text(sql))
        keys = list(result.keys())
        for i, row in enumerate(result.mappings()):
            if i >= row_limit:
                break
            rows.append({k: row.get(k) for k in keys})
    return rows
