# app/text_to_sql/executor.py
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings


def execute(sql: str, *, dialect: str, row_limit: int) -> List[Dict[str, Any]]:
    d = (dialect or settings.db_dialect or "oracle").lower().strip()

    if d == "oracle":
        from app.db.connectors.oracle import execute_sql  # noqa
        return execute_sql(sql, row_limit=row_limit)

    if d == "postgres":
        from app.db.connectors.postgres import execute_sql  # noqa
        return execute_sql(sql, row_limit=row_limit)

    raise ValueError(f"Unsupported dialect: {d}")


def count(sql: str, *, dialect: str) -> int:
    d = (dialect or settings.db_dialect or "oracle").lower().strip()

    if d == "oracle":
        from app.db.connectors.oracle import count_sql  # noqa
        return count_sql(sql)

    if d == "postgres":
        from app.db.connectors.postgres import count_sql  # noqa
        return count_sql(sql)

    raise ValueError(f"Unsupported dialect: {d}")
