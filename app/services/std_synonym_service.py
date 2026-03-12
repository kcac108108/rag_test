# STD_SYNONYM_SERVICE_FULL_REPLACE_v7
# - ✅ generate: "학습용 중복 생성" 허용 (단, P는 중복 금지)
# - approve: weight learning (prev_status == 'P' 인 경우만 +STEP, cap MAX)
# - reject: reject_reason 저장 + updated_at 갱신
# - list: status=ALL 지원

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text

from app.db.connectors.oracle import get_engine

OWNER = "ADIM"  # 운영정책: DBA 스키마 소유 유지

# -----------------------------
# Weight learning params
# -----------------------------
BASE_WEIGHT = 0.80
WEIGHT_STEP = 0.20
MAX_WEIGHT = 3.00


# -----------------------------
# Small utils (safe row access)
# -----------------------------
def _row_get_any(row: Any, *keys: str) -> Any:
    if row is None:
        return None
    for k in keys:
        if k in row:
            return row[k]
        lk = k.lower()
        if lk in row:
            return row[lk]
        uk = k.upper()
        if uk in row:
            return row[uk]
    return None


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


# -----------------------------
# Column resolver
# -----------------------------
def _fetch_columns(owner: str, table_name: str) -> List[str]:
    eng = get_engine()
    sql = """
        SELECT COLUMN_NAME
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :owner
          AND TABLE_NAME = :table_name
        ORDER BY COLUMN_ID
    """
    with eng.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"owner": owner.upper(), "table_name": table_name.upper()},
        ).all()
    return [str(r[0]) for r in rows]


def _pick_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    cset = set(cols)
    for c in candidates:
        if c in cset:
            return c
    return None


def _resolve_schema() -> Dict[str, Dict[str, str]]:
    cols_001 = _fetch_columns(OWNER, "TE_STD001M")
    cols_002 = _fetch_columns(OWNER, "TE_STD002L")
    cols_005 = _fetch_columns(OWNER, "TE_STD005T")
    cols_007 = _fetch_columns(OWNER, "TE_STD007T")

    # TE_STD001M
    m_std_id = _pick_col(cols_001, ["STD_ID"])
    m_std_nm = _pick_col(cols_001, ["STD_NM", "STD_NAME"])
    if not m_std_id or not m_std_nm:
        raise RuntimeError(f"TE_STD001M 컬럼 매핑 실패. 실제={cols_001}")

    # TE_STD002L
    l_syn_id = _pick_col(cols_002, ["SYN_ID", "SYNONYM_ID", "ID"])  # optional
    l_std_id = _pick_col(cols_002, ["STD_ID"])
    l_syn_nm = _pick_col(cols_002, ["SYNONYM", "SYN_NM", "SYN_NAME"])
    l_weight = _pick_col(cols_002, ["WEIGHT"])
    l_active = _pick_col(cols_002, ["IS_ACTIVE", "ACTIVE_YN"])
    if not l_std_id or not l_syn_nm:
        raise RuntimeError(f"TE_STD002L 컬럼 매핑 실패. 실제={cols_002}")

    # TE_STD005T
    f_std_id = _pick_col(cols_005, ["PICKED_STD_ID", "STD_ID", "PICK_STD_ID"])
    f_input = _pick_col(cols_005, ["INPUT_NM", "INPUT_NAME", "RAW_TEXT"])
    f_correct = _pick_col(cols_005, ["IS_CORRECT", "CORRECT_YN", "IS_OK", "OK_YN"])
    if not f_std_id or not f_input or not f_correct:
        raise RuntimeError(
            "TE_STD005T 컬럼명이 예상과 다릅니다. "
            f"STD_ID={f_std_id}, INPUT={f_input}, CORRECT={f_correct}, 실제={cols_005}"
        )

    # TE_STD007T
    s_sug_id = _pick_col(cols_007, ["SUG_ID", "SUGGEST_ID", "ID"])
    s_std_id = _pick_col(cols_007, ["STD_ID"])
    s_input = _pick_col(cols_007, ["INPUT_NM", "INPUT_NAME"])
    s_weight = _pick_col(cols_007, ["SUG_WEIGHT", "WEIGHT", "SCORE"])  # optional
    s_status = _pick_col(cols_007, ["STATUS"])  # optional
    s_source = _pick_col(cols_007, ["SOURCE_TYPE", "SRC_TYPE", "SOURCE"])  # optional
    s_created = _pick_col(cols_007, ["CREATED_AT", "CREATED_DT", "CRT_DTM"])  # optional
    s_updated = _pick_col(cols_007, ["UPDATED_AT", "UPDATED_DT", "UPD_DTM"])  # optional
    s_reject_reason = _pick_col(cols_007, ["REJECT_REASON", "REJECT_RSN", "REJECT_MSG"])  # optional

    if not s_sug_id or not s_std_id or not s_input:
        raise RuntimeError(f"TE_STD007T 컬럼 매핑 실패. 실제={cols_007}")

    return {
        "001": {"STD_ID": m_std_id, "STD_NM": m_std_nm},
        "002": {
            "SYN_ID": l_syn_id or "",
            "STD_ID": l_std_id,
            "SYN_NM": l_syn_nm,
            "WEIGHT": l_weight or "",
            "IS_ACTIVE": l_active or "",
        },
        "005": {"STD_ID": f_std_id, "INPUT": f_input, "CORRECT": f_correct},
        "007": {
            "SUG_ID": s_sug_id,
            "STD_ID": s_std_id,
            "INPUT": s_input,
            "WEIGHT": s_weight or "",
            "STATUS": s_status or "",
            "SOURCE": s_source or "",
            "CREATED_AT": s_created or "",
            "UPDATED_AT": s_updated or "",
            "REJECT_REASON": s_reject_reason or "",
        },
    }


# -----------------------------
# Chroma incremental upsert
# -----------------------------
def _chroma_upsert_synonym(syn_id: int, synonym_nm: str, std_id: int, std_name: str) -> None:
    from langchain_core.documents import Document
    from app.rag.vectorstore import get_vectorstore

    vs = get_vectorstore()
    doc_id = f"std_synonym:{syn_id}"

    doc = Document(
        page_content=synonym_nm,
        metadata={"namespace": "std_synonym", "id": doc_id, "std_id": std_id, "std_name": std_name},
    )

    # best-effort overwrite
    try:
        vs._collection.delete(ids=[doc_id])  # type: ignore[attr-defined]
    except Exception:
        pass

    vs.add_documents([doc], ids=[doc_id])


def _fetch_std_names(std_ids: List[int]) -> Dict[int, str]:
    std_ids = sorted({int(x) for x in std_ids if x is not None})
    if not std_ids:
        return {}
    m = _resolve_schema()
    m_std_id = m["001"]["STD_ID"]
    m_std_nm = m["001"]["STD_NM"]

    binds = []
    params: Dict[str, Any] = {}
    for i, sid in enumerate(std_ids):
        k = f"b{i}"
        binds.append(f":{k}")
        params[k] = sid

    sql = f"""
        SELECT M.{m_std_id} AS STD_ID, M.{m_std_nm} AS STD_NM
        FROM {OWNER}.TE_STD001M M
        WHERE M.{m_std_id} IN ({", ".join(binds)})
    """
    eng = get_engine()
    out: Dict[int, str] = {}
    with eng.connect() as conn:
        rows = conn.execute(text(sql), params).all()
        for r in rows:
            sid = _to_int(r[0])
            nm = r[1]
            if sid is not None and nm is not None:
                out[sid] = str(nm)
    return out


# -----------------------------
# Status update (UPDATED_AT auto)
# -----------------------------
def _update_status_and_ts(conn, m: Dict[str, Dict[str, str]], sug_id: int, new_status: str) -> Optional[str]:
    s_sug_id = m["007"]["SUG_ID"]
    s_status = m["007"]["STATUS"]
    s_updated = m["007"]["UPDATED_AT"]

    if not s_status:
        return None

    sql_prev = f"""
        SELECT S.{s_status}
        FROM {OWNER}.TE_STD007T S
        WHERE S.{s_sug_id} = :sug_id
        FOR UPDATE
    """
    r = conn.execute(text(sql_prev), {"sug_id": int(sug_id)}).first()
    prev = str(r[0]) if r and r[0] is not None else None

    set_parts = [f"{s_status} = :st"]
    params = {"st": new_status, "sug_id": int(sug_id)}

    if s_updated:
        set_parts.append(f"{s_updated} = SYSTIMESTAMP")

    sql_upd = f"""
        UPDATE {OWNER}.TE_STD007T
        SET {", ".join(set_parts)}
        WHERE {s_sug_id} = :sug_id
    """
    conn.execute(text(sql_upd), params)
    return prev


# -----------------------------
# ✅ Generate suggestions (학습용 중복 생성 허용)
# -----------------------------
def generate_synonym_suggestions(default_weight: float = BASE_WEIGHT) -> Dict[str, int]:
    """
    개선된 정책:
    - 이미 TE_STD002L에 존재하더라도 학습용으로 제안 생성 허용
    - 단, 같은 (STD_ID, INPUT_NM)에 대해 STATUS='P' 제안이 이미 있으면 중복 생성 금지
    - ✅ TE_STD005T에 동일 피드백이 여러 건 있어도, generate 1회 실행당 (STD_ID, INPUT_NM) 1건만 생성(DISTINCT)
    """
    m = _resolve_schema()

    f_std_id = m["005"]["STD_ID"]
    f_input = m["005"]["INPUT"]
    f_correct = m["005"]["CORRECT"]

    s_std_id = m["007"]["STD_ID"]
    s_input = m["007"]["INPUT"]
    s_weight = m["007"]["WEIGHT"]
    s_status = m["007"]["STATUS"]
    s_source = m["007"]["SOURCE"]

    insert_cols: List[str] = [s_std_id, s_input]
    select_exprs: List[str] = [f"F.{f_std_id} AS {s_std_id}", f"F.{f_input} AS {s_input}"]
    params = {"w": float(default_weight)}

    if s_weight:
        insert_cols.append(s_weight)
        select_exprs.append(f":w AS {s_weight}")

    if s_status:
        insert_cols.append(s_status)
        select_exprs.append(f"'P' AS {s_status}")

    if s_source:
        insert_cols.append(s_source)
        select_exprs.append(f"'FEEDBACK' AS {s_source}")

    # ✅ 핵심: P 상태만 중복 방지
    if s_status:
        not_exists_pending = f"""
          AND NOT EXISTS (
                SELECT 1
                FROM {OWNER}.TE_STD007T S
                WHERE S.{s_std_id} = F.{f_std_id}
                  AND S.{s_input} = F.{f_input}
                  AND S.{s_status} = 'P'
          )
        """
    else:
        not_exists_pending = f"""
          AND NOT EXISTS (
                SELECT 1
                FROM {OWNER}.TE_STD007T S
                WHERE S.{s_std_id} = F.{f_std_id}
                  AND S.{s_input} = F.{f_input}
          )
        """

    # ✅ TE_STD005T에서 DISTINCT로 (STD_ID, INPUT_NM) 조합을 1번만 뽑아냄
    sql = f"""
        INSERT INTO {OWNER}.TE_STD007T ({", ".join(insert_cols)})
        SELECT {", ".join(select_exprs)}
        FROM (
            SELECT DISTINCT
                   F0.{f_std_id} AS {f_std_id},
                   F0.{f_input}  AS {f_input}
            FROM {OWNER}.TE_STD005T F0
            WHERE F0.{f_correct} = 'Y'
              AND F0.{f_std_id} IS NOT NULL
              AND F0.{f_input} IS NOT NULL
        ) F
        WHERE 1=1
          {not_exists_pending}
    """

    eng = get_engine()
    with eng.begin() as conn:
        res = conn.execute(text(sql), params)

    return {"inserted_rows": int(res.rowcount or 0)}


# -----------------------------
# Approve suggestion (✅ weight learning)
# -----------------------------
def approve_synonym_suggestion(sug_id: int, reindex: bool = True) -> Dict[str, object]:
    m = _resolve_schema()

    s_sug_id = m["007"]["SUG_ID"]
    s_std_id = m["007"]["STD_ID"]
    s_input = m["007"]["INPUT"]
    s_weight = m["007"]["WEIGHT"]
    s_status = m["007"]["STATUS"]

    l_syn_id = m["002"]["SYN_ID"]
    l_std_id = m["002"]["STD_ID"]
    l_syn_nm = m["002"]["SYN_NM"]
    l_weight = m["002"]["WEIGHT"]
    l_active = m["002"]["IS_ACTIVE"]

    m_std_id = m["001"]["STD_ID"]
    m_std_nm = m["001"]["STD_NM"]

    eng = get_engine()

    inserted = 0
    syn_id_val: Optional[int] = None
    std_id_val: int
    input_nm_val: str
    weight_val: float
    prev_status: Optional[str] = None
    std_name_val: str = ""

    with eng.begin() as conn:
        # 1) lock suggestion row
        sel_cols = [f"S.{s_sug_id}", f"S.{s_std_id}", f"S.{s_input}"]
        if s_weight:
            sel_cols.append(f"S.{s_weight}")
        if s_status:
            sel_cols.append(f"S.{s_status}")

        sql_sel = f"""
            SELECT {", ".join(sel_cols)}
            FROM {OWNER}.TE_STD007T S
            WHERE S.{s_sug_id} = :sug_id
            FOR UPDATE
        """
        row = conn.execute(text(sql_sel), {"sug_id": int(sug_id)}).first()
        if not row:
            return {"ok": False, "error": "SUGGESTION_NOT_FOUND", "sug_id": int(sug_id)}

        idx = 0
        _ = int(row[idx]); idx += 1
        std_id_val = int(row[idx]); idx += 1
        input_nm_val = str(row[idx]); idx += 1

        # suggestion weight (optional)
        weight_val = BASE_WEIGHT
        if s_weight:
            weight_val = float(row[idx]) if row[idx] is not None else BASE_WEIGHT
            idx += 1

        # 2) update status to 'A' (and UPDATED_AT if exists) + get prev_status
        if s_status:
            prev_status = _update_status_and_ts(conn, m, sug_id, "A")

        # 3) Upsert to TE_STD002L with learning
        sql_exist = f"""
            SELECT
                {f"L.{l_syn_id} AS SYN_ID," if l_syn_id else ""}
                {f"L.{l_weight} AS WEIGHT" if l_weight else "NULL AS WEIGHT"}
            FROM {OWNER}.TE_STD002L L
            WHERE L.{l_std_id} = :std_id
              AND L.{l_syn_nm} = :syn_nm
            FOR UPDATE
        """
        exists_row = conn.execute(text(sql_exist), {"std_id": std_id_val, "syn_nm": input_nm_val}).first()

        if exists_row:
            # already exists -> learning update (only if weight col exists)
            if l_syn_id:
                syn_id_val = int(exists_row[0]) if exists_row[0] is not None else None
                cur_weight = float(exists_row[1]) if (l_weight and exists_row[1] is not None) else None
            else:
                cur_weight = float(exists_row[0]) if (l_weight and exists_row[0] is not None) else None

            if l_weight and (prev_status == "P"):
                cur = cur_weight if cur_weight is not None else BASE_WEIGHT
                new_w = min(cur + WEIGHT_STEP, MAX_WEIGHT)
                sql_upw = f"""
                    UPDATE {OWNER}.TE_STD002L
                    SET {l_weight} = :nw
                    WHERE {l_std_id} = :std_id
                      AND {l_syn_nm} = :syn_nm
                """
                conn.execute(text(sql_upw), {"nw": float(new_w), "std_id": std_id_val, "syn_nm": input_nm_val})
                weight_val = float(new_w)
            else:
                if cur_weight is not None:
                    weight_val = float(cur_weight)

            inserted = 0

        else:
            # not exists -> insert
            insert_cols = [l_std_id, l_syn_nm]
            insert_vals = [":std_id", ":syn_nm"]
            ins_w = max(float(weight_val), float(BASE_WEIGHT))

            params = {"std_id": std_id_val, "syn_nm": input_nm_val, "w": float(ins_w)}

            if l_weight:
                insert_cols.append(l_weight)
                insert_vals.append(":w")
            if l_active:
                insert_cols.append(l_active)
                insert_vals.append("'Y'")

            sql_ins = f"""
                INSERT INTO {OWNER}.TE_STD002L ({", ".join(insert_cols)})
                SELECT {", ".join(insert_vals)}
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM {OWNER}.TE_STD002L L
                    WHERE L.{l_std_id} = :std_id
                      AND L.{l_syn_nm} = :syn_nm
                )
            """
            r_ins = conn.execute(text(sql_ins), params)
            inserted = int(r_ins.rowcount or 0)
            weight_val = float(ins_w)

            if l_syn_id:
                r = conn.execute(
                    text(
                        f"""
                        SELECT L.{l_syn_id}
                        FROM {OWNER}.TE_STD002L L
                        WHERE L.{l_std_id} = :std_id
                          AND L.{l_syn_nm} = :syn_nm
                        """
                    ),
                    {"std_id": std_id_val, "syn_nm": input_nm_val},
                ).first()
                if r and r[0] is not None:
                    syn_id_val = int(r[0])

        # fetch std_name for reindex
        rstd = conn.execute(
            text(
                f"""
                SELECT M.{m_std_nm}
                FROM {OWNER}.TE_STD001M M
                WHERE M.{m_std_id} = :std_id
                """
            ),
            {"std_id": std_id_val},
        ).first()
        std_name_val = str(rstd[0]) if rstd and rstd[0] is not None else ""

    reindexed = False
    if reindex and syn_id_val is not None and std_name_val:
        try:
            _chroma_upsert_synonym(syn_id_val, input_nm_val, std_id_val, std_name_val)
            reindexed = True
        except Exception:
            reindexed = False

    return {
        "ok": True,
        "sug_id": int(sug_id),
        "std_id": std_id_val,
        "synonym": input_nm_val,
        "weight": float(weight_val),
        "prev_status": prev_status,
        "approved": True,
        "inserted_to_std002l": bool(inserted),
        "syn_id": syn_id_val,
        "reindexed": reindexed,
        "error": None,
    }


# -----------------------------
# Reject suggestion
# -----------------------------
def reject_synonym_suggestion(sug_id: int, reason: Optional[str] = None) -> Dict[str, object]:
    m = _resolve_schema()
    if not m["007"]["STATUS"]:
        return {"ok": False, "error": "STATUS_COLUMN_NOT_FOUND", "sug_id": int(sug_id)}

    s_reject = m["007"]["REJECT_REASON"]

    eng = get_engine()
    with eng.begin() as conn:
        s_sug_id = m["007"]["SUG_ID"]

        chk = conn.execute(
            text(f"SELECT 1 FROM {OWNER}.TE_STD007T S WHERE S.{s_sug_id} = :sug_id FOR UPDATE"),
            {"sug_id": int(sug_id)},
        ).first()
        if not chk:
            return {"ok": False, "error": "SUGGESTION_NOT_FOUND", "sug_id": int(sug_id)}

        prev_status = _update_status_and_ts(conn, m, sug_id, "R")

        if s_reject:
            sql_r = f"""
                UPDATE {OWNER}.TE_STD007T
                SET {s_reject} = :rsn
                WHERE {s_sug_id} = :sug_id
            """
            conn.execute(text(sql_r), {"rsn": (reason or "")[:500], "sug_id": int(sug_id)})

    return {
        "ok": True,
        "sug_id": int(sug_id),
        "rejected": True,
        "prev_status": prev_status,
        "reason": reason,
        "error": None,
    }


# -----------------------------
# Batch approve / reject
# -----------------------------
def batch_approve_synonym_suggestions(sug_ids: List[int], reindex: bool = True) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    to_reindex: List[Tuple[int, str, int]] = []

    for sid in sug_ids:
        r = approve_synonym_suggestion(int(sid), reindex=False)
        results.append(r)
        if r.get("ok") and r.get("syn_id") and r.get("synonym") and r.get("std_id"):
            to_reindex.append((int(r["syn_id"]), str(r["synonym"]), int(r["std_id"])))

    reindexed_count = 0
    if reindex and to_reindex:
        std_names = _fetch_std_names([x[2] for x in to_reindex])
        for syn_id, synonym, std_id in to_reindex:
            std_name = std_names.get(std_id, "")
            if not std_name:
                continue
            try:
                _chroma_upsert_synonym(syn_id, synonym, std_id, std_name)
                reindexed_count += 1
            except Exception:
                pass

    approved_ok = sum(1 for r in results if r.get("ok") and r.get("approved"))
    errors = sum(1 for r in results if not r.get("ok"))

    return {
        "ok": True,
        "requested": len(sug_ids),
        "approved_ok": approved_ok,
        "errors": errors,
        "reindexed_count": reindexed_count if reindex else 0,
        "results": results,
    }


def batch_reject_synonym_suggestions(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for it in items:
        sid = int(it.get("sug_id"))
        rsn = it.get("reason")
        r = reject_synonym_suggestion(sid, reason=rsn)
        results.append(r)

    rejected_ok = sum(1 for r in results if r.get("ok") and r.get("rejected"))
    errors = sum(1 for r in results if not r.get("ok"))

    return {
        "ok": True,
        "requested": len(items),
        "rejected_ok": rejected_ok,
        "errors": errors,
        "results": results,
    }


# -----------------------------
# List suggestions
# -----------------------------
def list_synonym_suggestions(
    status: str = "P",
    limit: int = 50,
    offset: int = 0,
    std_id: Optional[int] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    m = _resolve_schema()

    s_sug_id = m["007"]["SUG_ID"]
    s_std_id = m["007"]["STD_ID"]
    s_input = m["007"]["INPUT"]
    s_weight = m["007"]["WEIGHT"]
    s_status = m["007"]["STATUS"]
    s_source = m["007"]["SOURCE"]
    s_created = m["007"]["CREATED_AT"]
    s_updated = m["007"]["UPDATED_AT"]
    s_reject = m["007"]["REJECT_REASON"]

    m_std_id = m["001"]["STD_ID"]
    m_std_nm = m["001"]["STD_NM"]

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    select_cols = [
        f"S.{s_sug_id} AS sug_id",
        f"S.{s_std_id} AS std_id",
        f"M.{m_std_nm} AS std_name",
        f"S.{s_input} AS input_nm",
    ]
    if s_weight:
        select_cols.append(f"S.{s_weight} AS sug_weight")
    if s_status:
        select_cols.append(f"S.{s_status} AS status")
    if s_source:
        select_cols.append(f"S.{s_source} AS source_type")
    if s_created:
        select_cols.append(f"S.{s_created} AS created_at")
    if s_updated:
        select_cols.append(f"S.{s_updated} AS updated_at")
    if s_reject:
        select_cols.append(f"S.{s_reject} AS reject_reason")

    where = ["1=1"]
    params: Dict[str, Any] = {}

    if std_id is not None:
        where.append(f"S.{s_std_id} = :std_id")
        params["std_id"] = int(std_id)

    st = (status or "").upper()
    if s_status and st and st != "ALL":
        where.append(f"S.{s_status} = :status")
        params["status"] = st

    if q:
        where.append(f"(UPPER(S.{s_input}) LIKE UPPER(:q) OR UPPER(M.{m_std_nm}) LIKE UPPER(:q))")
        params["q"] = f"%{q}%"

    base_from = f"""
        FROM {OWNER}.TE_STD007T S
        JOIN {OWNER}.TE_STD001M M
          ON M.{m_std_id} = S.{s_std_id}
        WHERE {" AND ".join(where)}
    """

    sql_count = f"SELECT COUNT(*) {base_from}"
    sql_list = f"""
        SELECT {", ".join(select_cols)}
        {base_from}
        ORDER BY S.{s_sug_id} DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    params["offset"] = offset
    params["limit"] = limit

    eng = get_engine()
    with eng.connect() as conn:
        total = int(conn.execute(text(sql_count), params).scalar() or 0)
        rows = conn.execute(text(sql_list), params).mappings().all()

    items_out: List[Dict[str, Any]] = []
    for r in rows:
        sug_id_val = _to_int(_row_get_any(r, "sug_id", "SUG_ID"))
        std_id_val = _to_int(_row_get_any(r, "std_id", "STD_ID"))
        if sug_id_val is None or std_id_val is None:
            continue

        items_out.append(
            {
                "sug_id": sug_id_val,
                "std_id": std_id_val,
                "std_name": _row_get_any(r, "std_name", "STD_NAME"),
                "input_nm": _row_get_any(r, "input_nm", "INPUT_NM"),
                "sug_weight": _to_float(_row_get_any(r, "sug_weight", "SUG_WEIGHT")),
                "status": _row_get_any(r, "status", "STATUS"),
                "source_type": _row_get_any(r, "source_type", "SOURCE_TYPE"),
                "created_at": str(_row_get_any(r, "created_at", "CREATED_AT"))
                if _row_get_any(r, "created_at", "CREATED_AT") is not None
                else None,
                "updated_at": str(_row_get_any(r, "updated_at", "UPDATED_AT"))
                if _row_get_any(r, "updated_at", "UPDATED_AT") is not None
                else None,
                "reject_reason": _row_get_any(r, "reject_reason", "REJECT_REASON"),
            }
        )

    return {"total": total, "limit": limit, "offset": offset, "items": items_out}