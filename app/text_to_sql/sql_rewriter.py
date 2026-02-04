from __future__ import annotations

import re
from app.core.config import settings
from app.text_to_sql.prompts import sql_system_prompt


def _oracle_fix(sql: str, row_limit: int) -> str:
    s = sql.strip().rstrip(";").strip()

    # LIMIT -> FETCH FIRST
    m = re.search(r"\bLIMIT\s+(\d+)\b", s, flags=re.IGNORECASE)
    if m:
        n = m.group(1)
        s = re.sub(r"\bLIMIT\s+\d+\b", f"FETCH FIRST {n} ROWS ONLY", s, flags=re.IGNORECASE)

    # 혹시 제한이 아예 없으면 row_limit 넣기
    if row_limit and re.search(r"\bFETCH\s+FIRST\s+\d+\s+ROWS\s+ONLY\b", s, re.IGNORECASE) is None:
        s = s + f" FETCH FIRST {int(row_limit)} ROWS ONLY"

    return s


def rewrite_sql(question: str, sql: str, error: str, context: str, dialect: str, row_limit: int) -> str:
    """
    실행 실패 시 SQL을 수정해 재시도하는 용도.
    우선은 안전하게 'Oracle LIMIT 문제'만 자동 수정.
    (원하면 LLM 기반 리라이트도 추가 가능)
    """
    d = (dialect or "postgres").lower().strip()

    # 1) 간단 규칙 기반 수정(빠르고 안정적)
    if d == "oracle":
        return _oracle_fix(sql, row_limit=row_limit)

    # 2) 기본은 원본 반환
    # (필요 시 postgres 케이스도 여기서 수정 가능)
    return sql
