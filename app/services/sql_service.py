# app/services/sql_service.py
from __future__ import annotations

import re
from typing import Optional

from app.core.config import settings
from app.schemas.sql import SQLQueryRequest, SQLQueryResponse
from app.text_to_sql.context_builder import build_context
from app.text_to_sql.sql_generator import generate_sql
from app.text_to_sql.sql_validator import validate_sql
from app.text_to_sql.executor import execute, count
from app.text_to_sql.sql_rewriter import rewrite_sql
from app.text_to_sql.result_formatter import format_rows


# ----------------------------
# Rank / Window helpers
# ----------------------------
_RANK_DIGIT_RE = re.compile(r"(\d+)\s*(위|등|번째)")
_RANK_KOREAN_RE = re.compile(r"(한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*번째")
_TOPN_RE = re.compile(r"(상위|TOP)\s*(\d+)", re.IGNORECASE)

_KOREAN_ORDINAL_MAP = {
    "한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5,
    "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
}


def _has_window_function(sql: str) -> bool:
    u = (sql or "").upper()
    return (
        "RANK() OVER" in u
        or "DENSE_RANK() OVER" in u
        or "ROW_NUMBER() OVER" in u
    )


def _extract_rank_n(question: str) -> Optional[int]:
    q = question or ""
    m = _RANK_DIGIT_RE.search(q)
    if m:
        return int(m.group(1))
    m = _RANK_KOREAN_RE.search(q)
    if m:
        return _KOREAN_ORDINAL_MAP.get(m.group(1))
    return None


def _looks_like_topn_question(question: str) -> bool:
    return bool(_TOPN_RE.search(question or ""))


def _strip_sql_fences(sql: str) -> str:
    s = (sql or "").strip()
    s = re.sub(r"^\s*```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def _normalize_semicolon(sql: str) -> str:
    s = (sql or "").strip().rstrip(";").strip()
    return s + ";"


_DUP_AS_RE = re.compile(r"\bAS\s+([A-Z_][A-Z0-9_]*)(?:\s+AS\s+\1)+", re.I)


def _dedupe_alias(sql: str) -> str:
    s = sql or ""
    for _ in range(5):
        new = re.sub(_DUP_AS_RE, r"AS \1", s)
        if new == s:
            break
        s = new
    return s


def _sanitize_sql(sql: str) -> str:
    s = _strip_sql_fences(sql)
    s = _dedupe_alias(s)
    return _normalize_semicolon(s)


def _upper_sql(sql: str) -> str:
    if not sql:
        return sql
    out = []
    in_str = False
    for ch in sql:
        if ch == "'":
            in_str = not in_str
            out.append(ch)
        else:
            out.append(ch if in_str else ch.upper())
    return "".join(out)


def _ensure_limit(sql: str, row_limit: int, dialect: str) -> str:
    s = sql.rstrip(";").strip()
    if dialect.lower() == "oracle":
        return s + ";"
    if "LIMIT" in s.upper():
        return s + ";"
    return f"{s}\nLIMIT {row_limit};"


def _build_summary(returned: int, row_limit: int, total: Optional[int]) -> tuple[str, bool]:
    if total is not None:
        if returned >= row_limit and total > row_limit:
            return f"총 {total}건 중 {returned}건 표시", True
        return f"총 {total}건 표시", False
    if returned >= row_limit:
        return f"{returned}건 표시 (제한됨)", True
    return f"{returned}건 표시", False


def _enforce_rank_only_if_needed(*, question, sql, context, dialect, row_limit):
    rank_n = _extract_rank_n(question)
    if not rank_n or _looks_like_topn_question(question):
        return sql

    policy = (
        "ORACLE RANK RULE:\n"
        "- NEVER use RANK() in HAVING or WHERE.\n"
        "- Use CTE: base -> ranked -> outer WHERE RNK = N.\n"
        "- Do NOT use SELECT *.\n"
        "- Do NOT duplicate aliases.\n"
        "- Output SQL only.\n"
    )
    rewritten = rewrite_sql(question, sql, policy, context, dialect, row_limit)
    return _sanitize_sql(rewritten)


class SQLService:
    def handle(self, req: SQLQueryRequest) -> SQLQueryResponse:
        dialect = req.dialect or settings.db_dialect
        row_limit = min(req.row_limit, settings.max_rows)

        include_sources = bool(getattr(req, "include_sources", False))
        include_total = bool(getattr(req, "include_total", False))

        context, sources = build_context(req.question, req.top_k)
        resp_sources = sources if include_sources else None

        sql = generate_sql(req.question, context, dialect, row_limit)
        sql = _sanitize_sql(sql)

        sql = _enforce_rank_only_if_needed(
            question=req.question,
            sql=sql,
            context=context,
            dialect=dialect,
            row_limit=row_limit,
        )

        sql = _ensure_limit(sql, row_limit, dialect)
        sql = _upper_sql(sql)

        ok, warnings = validate_sql(sql)
        if not ok:
            return SQLQueryResponse(sql=sql, summary="SQL rejected", results=[], sources=resp_sources)

        if req.dry_run:
            return SQLQueryResponse(sql=sql, summary="Dry run", results=[], sources=None)

        try:
            # ✅ 핵심 수정: WINDOW FUNCTION 있으면 COUNT 안 함
            total = None
            if include_total and not _has_window_function(sql):
                total = count(sql, dialect=dialect)

            rows = execute(sql, dialect=dialect, row_limit=row_limit)
            rows = rows[:row_limit]

            _, results = format_rows(rows)
            summary, is_limited = _build_summary(len(rows), row_limit, total)

            return SQLQueryResponse(
                sql=sql,
                summary=summary,
                results=results,
                sources=resp_sources,
                total_rows=total,
                is_limited=is_limited,
            )

        except Exception as e:
            return SQLQueryResponse(
                sql=sql,
                summary=f"Execution failed: {e}",
                results=[],
                sources=resp_sources,
            )
