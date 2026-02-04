# app/db/connectors/oracle.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import settings

_ENGINE: Optional[Engine] = None

_FETCH_FIRST_RE = re.compile(r"\bFETCH\s+FIRST\s+\d+\s+ROWS\s+ONLY\b", re.IGNORECASE)


def _parse_oracle_dsn(dsn: str) -> Tuple[str, int, Optional[str]]:
    s = (dsn or "").strip()
    s = re.sub(r"^\s*//", "", s)

    m = re.match(r"^(?P<host>[^:/]+):(?P<port>\d+)/(?:\s*)(?P<svc>[^/?]+)\s*$", s)
    if m:
        return m.group("host"), int(m.group("port")), m.group("svc")

    m = re.match(r"^(?P<host>[^:/]+):(?P<port>\d+):(?P<sid>[^/?]+)\s*$", s)
    if m:
        return m.group("host"), int(m.group("port")), m.group("sid")

    m = re.match(r"^(?P<host>[^:/]+):(?P<port>\d+)\s*$", s)
    if m:
        return m.group("host"), int(m.group("port")), None

    raise ValueError(f"Invalid ORACLE_DSN format: {dsn!r}")


def _strip_trailing_semicolon(sql: str) -> str:
    """DBAPI로 실행할 때는 세미콜론이 ORA-00933를 유발할 수 있으므로 제거."""
    s = (sql or "").strip()
    # 여러 개 있을 수도 있으니 끝의 ;만 반복 제거
    while s.endswith(";"):
        s = s[:-1].rstrip()
    return s


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    dsn = getattr(settings, "oracle_dsn", None) or getattr(settings, "ORACLE_DSN", None)
    user = getattr(settings, "oracle_user", None) or getattr(settings, "ORACLE_USER", None)
    pwd = getattr(settings, "oracle_password", None) or getattr(settings, "ORACLE_PASSWORD", None)

    if not (dsn and user and pwd):
        raise ValueError("Oracle settings missing: ORACLE_DSN/ORACLE_USER/ORACLE_PASSWORD")

    host, port, service = _parse_oracle_dsn(dsn)

    # ✅ 핵심: service_name을 명시해서 SID 인식 문제 회피
    if service:
        url = f"oracle+oracledb://{user}:{pwd}@{host}:{port}/?service_name={service}"
    else:
        url = f"oracle+oracledb://{user}:{pwd}@{host}:{port}/"

    _ENGINE = create_engine(url, pool_pre_ping=True)
    return _ENGINE


# -----------------------------
# Helpers: only for COUNT
# -----------------------------
def _strip_trailing_fetch_first(sql: str) -> str:
    s = _strip_trailing_semicolon(sql)
    s = re.sub(_FETCH_FIRST_RE, "", s).strip()
    return s


def _strip_trailing_order_by_top_level(sql: str) -> str:
    s = _strip_trailing_semicolon(sql)
    u = s.upper()

    depth = 0
    for i in range(len(s) - 1, -1, -1):
        ch = s[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            depth = max(depth - 1, 0)

        if depth == 0:
            idx = u.rfind("ORDER BY", 0, i + 1)
            if idx != -1:
                tail = u[idx:]
                if "OVER" in tail[:30]:
                    continue
                return s[:idx].rstrip()
    return s


def count_sql(sql: str) -> int:
    base = _strip_trailing_semicolon(sql)
    base = _strip_trailing_fetch_first(base)
    base = _strip_trailing_order_by_top_level(base)

    count_query = f"SELECT COUNT(*) AS CNT FROM ({base}) t"

    eng = get_engine()
    with eng.connect() as conn:
        row = conn.execute(text(count_query)).fetchone()
        if row is None:
            return 0
        try:
            return int(row[0])
        except Exception:
            return int(row["CNT"])


# -----------------------------
# Execute
# -----------------------------
def execute_sql(sql: str, *, row_limit: int = 200) -> List[Dict[str, Any]]:
    """
    ✅ 실행은 원본 SQL을 최대한 유지
    ✅ 단, DBAPI 실행 시 trailing ';'는 제거 (ORA-00933 방지)
    ✅ FETCH FIRST 없으면 row_limit 추가
    """
    s = _strip_trailing_semicolon(sql)

    if not re.search(_FETCH_FIRST_RE, s):
        s = f"{s}\nFETCH FIRST {int(row_limit)} ROWS ONLY"

    eng = get_engine()
    with eng.connect() as conn:
        rs = conn.execute(text(s))
        rows = rs.fetchall()
        cols = list(rs.keys())
        return [{cols[i]: r[i] for i in range(len(cols))} for r in rows]
