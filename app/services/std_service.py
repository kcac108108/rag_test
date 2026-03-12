from __future__ import annotations

import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy import text

from app.core.config import settings
from app.db.connectors.oracle import get_engine
from app.rag.retriever import retrieve


DEFAULT_TOPK = 5
DEFAULT_MIN_SCORE = 0.8

# Abstain 기본 정책값
DEFAULT_ABSTAIN_ENABLED = True
DEFAULT_CONFIDENCE_MIN = 1.15
DEFAULT_MARGIN_MIN = 0.15
DEFAULT_ABSTAIN_NO2_SCORE = 1.0

# 일반어 감지 (정교화)
STRONG_GENERIC_TERMS = [
    "금속", "합금", "판재", "자재", "소재", "원자재", "제품", "부품", "재료",
    "샘플", "기타", "일반",
]
WEAK_GENERIC_TERMS = ["판", "재", "류", "용"]

SPECIFIC_TERMS = [
    "도금", "코팅", "니켈", "알루미늄", "구리", "철", "강", "강판", "스테인리스", "sus",
    "탄소강", "합성수지", "플라스틱", "폴리", "pp", "pe", "pvc",
    "압연", "열처리", "절단", "가공", "용접", "주조", "단조",
]

DEFAULT_GENERIC_FORCE_TOP1_MIN = 2.8

# -------------------------------
# PoC: WEIGHT 점수 반영(간단 버전)
# -------------------------------
# score = score * (1 + alpha*(weight-1))
POC_WEIGHT_ALPHA = 0.50
POC_WEIGHT_CAP = 3.00  # 과도한 폭주 방지

# -------------------------------
# ✅ Negative Gate (무관성 차단)
# -------------------------------
# "중고자동차" 같이 표준품명(금속/재질/공정/형상)과 무관한 입력이면 candidates 자체를 비움
DOMAIN_HINT_TERMS = sorted(
    set(
        STRONG_GENERIC_TERMS
        + [
            # 형상/품목 타입 힌트
            "판재", "시트", "코일", "호일",
            "환봉", "각봉", "파이프", "선재",
            "분말", "펠릿", "스크랩",
            "잉곳", "빌렛", "슬래브",

            # 재질/계열 힌트 (✅ 단일음절 제외)
            "니켈", "알루미늄", "구리", "철강", "스테인리스", "sus", "탄소강", "합금",

            # 표면처리
            "도금", "코팅",

            # 공정
            "압연", "열처리", "절단", "가공", "용접", "주조", "단조",
        ]
    )
)

# 짧고 애매한 단어는 out-of-domain 처리하지 않음(오탐 방지)
NEG_GATE_MIN_LEN = 3


def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _has_any_term(text: str, terms: List[str]) -> List[str]:
    return [t for t in terms if t and t in text]


def _is_out_of_domain(raw_text: str) -> Dict[str, Any]:
    """
    PoC용 간단 차단:
    - 입력이 너무 짧으면(out-of-domain 판단 보류)
    - 도메인 힌트 키워드(금속/재질/공정/형상)가 하나도 없으면 out-of-domain으로 간주
    """
    t = _normalize_text(raw_text)
    if not t:
        return {"out": True, "reason": "EMPTY"}

    # 너무 짧은 단어는 오탐 위험이 커서 차단 안 함 (예: "판", "재")
    if len(t) < NEG_GATE_MIN_LEN:
        return {"out": False, "reason": "TOO_SHORT_SKIP"}

    hits = _has_any_term(t, DOMAIN_HINT_TERMS)
    if hits:
        return {"out": False, "reason": f"HAS_DOMAIN_HINT:{','.join(sorted(set(hits)))}"}

    return {"out": True, "reason": "NO_DOMAIN_HINT"}


def _is_generic_input(raw_text: str) -> Dict[str, Any]:
    """
    - strong generic 포함 + 구체 키워드 없음 → generic
    - weak generic만 포함은 generic으로 올리지 않음
    - 구체 키워드가 있으면 generic=false
    """
    t = _normalize_text(raw_text)
    if not t:
        return {"generic": True, "generic_level": "strong", "reason": "EMPTY"}

    if len(t) <= 4:
        spec_hits = _has_any_term(t, SPECIFIC_TERMS)
        if spec_hits:
            return {"generic": False, "generic_level": None, "reason": f"SHORT_BUT_SPECIFIC:{','.join(spec_hits)}"}
        return {"generic": True, "generic_level": "strong", "reason": "TOO_SHORT"}

    strong_hits = _has_any_term(t, STRONG_GENERIC_TERMS)
    weak_hits = _has_any_term(t, WEAK_GENERIC_TERMS)
    spec_hits = _has_any_term(t, SPECIFIC_TERMS)

    if spec_hits:
        return {"generic": False, "generic_level": None, "reason": f"SPECIFIC:{','.join(spec_hits)}"}

    if strong_hits:
        return {"generic": True, "generic_level": "strong", "reason": f"STRONG_GENERIC:{','.join(sorted(set(strong_hits)))}"}

    if weak_hits:
        return {"generic": False, "generic_level": None, "reason": f"WEAK_GENERIC_ONLY:{','.join(sorted(set(weak_hits)))}"}

    return {"generic": False, "generic_level": None, "reason": None}


def _merge_candidates(master_hits, synonym_hits):
    merged: Dict[int, Dict[str, Any]] = {}

    def _add(hit, boost=1.0):
        metadata = hit.metadata or {}
        std_id = metadata.get("std_id")
        if not std_id:
            return

        std_id = int(std_id)

        if std_id not in merged:
            merged[std_id] = {
                "std_id": std_id,
                "std_name": metadata.get("std_name"),
                "score": 0.0,
                "sources": [],
            }

        merged[std_id]["score"] += (hit.score or 0) * boost
        merged[std_id]["sources"].append(metadata.get("namespace"))

    for h in master_hits:
        _add(h, boost=1.0)
    for h in synonym_hits:
        _add(h, boost=1.2)

    return sorted(merged.values(), key=lambda x: x["score"], reverse=True)


def _fetch_std_details(std_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not std_ids:
        return {}

    eng = get_engine()
    binds = {f"id{i}": int(v) for i, v in enumerate(std_ids)}
    in_list = ", ".join([f":id{i}" for i in range(len(std_ids))])

    sql = f"""
        SELECT
            STD_ID   AS std_id,
            STD_NM   AS std_nm,
            STD_DESC AS std_desc,
            HS_CODE  AS hs_code
        FROM TE_STD001M
        WHERE STD_ID IN ({in_list})
    """

    details: Dict[int, Dict[str, Any]] = {}
    with eng.connect() as conn:
        rows = conn.execute(text(sql), binds).mappings().all()
        for r in rows:
            sid = int(r["std_id"])
            details[sid] = {
                "std_id": sid,
                "std_name": r.get("std_nm"),
                "std_desc": r.get("std_desc"),
                "hs_code": r.get("hs_code"),
            }
    return details


def _fetch_exact_syn_weights(std_ids: List[int], syn_nm: str) -> Dict[int, float]:
    """
    PoC 핵심:
      - 후보 STD_ID들에 대해,
      - TE_STD002L에서 (STD_ID, SYN_NM=입력값) 의 WEIGHT를 가져온다.
      - 없으면 1.0으로 취급.
    """
    if not std_ids or not syn_nm:
        return {}

    eng = get_engine()
    binds = {f"id{i}": int(v) for i, v in enumerate(std_ids)}
    binds["syn_nm"] = syn_nm
    in_list = ", ".join([f":id{i}" for i in range(len(std_ids))])

    # ✅ SYN_NM 컬럼 사용
    sql = f"""
        SELECT
            STD_ID AS std_id,
            WEIGHT AS weight
        FROM TE_STD002L
        WHERE IS_ACTIVE = 'Y'
          AND SYN_NM = :syn_nm
          AND STD_ID IN ({in_list})
    """

    out: Dict[int, float] = {}
    with eng.connect() as conn:
        rows = conn.execute(text(sql), binds).mappings().all()
        for r in rows:
            try:
                sid = int(r["std_id"])
                w = float(r.get("weight") or 1.0)
                out[sid] = w
            except Exception:
                continue
    return out


def _apply_weight_boost(raw_text: str, candidates: List[Dict[str, Any]]) -> None:
    """
    candidates를 in-place로 업데이트:
      - score_raw 저장
      - weight 저장
      - score를 weight 보정 반영
    """
    if not candidates:
        return

    syn_nm = _normalize_text(raw_text)
    std_ids = [int(c["std_id"]) for c in candidates]
    w_map = _fetch_exact_syn_weights(std_ids, syn_nm)

    alpha = POC_WEIGHT_ALPHA
    cap = POC_WEIGHT_CAP

    for c in candidates:
        sid = int(c["std_id"])
        base = float(c.get("score") or 0.0)
        w = float(w_map.get(sid, 1.0) or 1.0)
        if w < 0:
            w = 1.0
        if w > cap:
            w = cap

        c["score_raw"] = base
        c["weight"] = w

        if w != 1.0:
            c["score"] = base * (1.0 + alpha * (w - 1.0))


def _compute_confidence_metrics(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return {"top1_score": None, "top2_score": None, "ratio": None, "margin": None}

    s1 = float(candidates[0].get("score") or 0.0)
    s2 = float(candidates[1].get("score") or 0.0) if len(candidates) >= 2 else None

    ratio = (s1 / s2) if (s2 is not None and s2 > 0) else None
    margin = (s1 - s2) if (s2 is not None) else None
    return {"top1_score": s1, "top2_score": s2, "ratio": ratio, "margin": margin}


def _should_abstain(candidates: List[Dict[str, Any]], confidence_min: float, margin_min: float, no2_min_score: float):
    m = _compute_confidence_metrics(candidates)
    s1 = m["top1_score"]
    s2 = m["top2_score"]
    ratio = m["ratio"]
    margin = m["margin"]

    if not candidates:
        return {"abstain": True, "reason": "NO_CANDIDATES", "metrics": m}

    if s2 is None:
        if s1 is None or s1 < float(no2_min_score):
            return {"abstain": True, "reason": "LOW_TOP1_SCORE_SINGLE", "metrics": m}
        return {"abstain": False, "reason": None, "metrics": m}

    if ratio is not None and ratio < float(confidence_min):
        return {"abstain": True, "reason": "LOW_RATIO", "metrics": m}

    if margin is not None and margin < float(margin_min):
        return {"abstain": True, "reason": "LOW_MARGIN", "metrics": m}

    return {"abstain": False, "reason": None, "metrics": m}


def _llm_rerank(raw_text: str, candidates: List[Dict[str, Any]], generic_info: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.openai_api_key:
        return {"candidates": candidates, "picked_std_id": None, "reason": None}

    if not candidates or len(candidates) < 2:
        return {"candidates": candidates, "picked_std_id": candidates[0]["std_id"] if candidates else None, "reason": None}

    topn = max(2, int(getattr(settings, "std_rerank_topn", 12) or 12))
    base = candidates[:topn]

    std_ids = [int(c["std_id"]) for c in base]
    detail_map = _fetch_std_details(std_ids)

    items = []
    for c in base:
        sid = int(c["std_id"])
        d = detail_map.get(sid, {})
        items.append(
            {
                "std_id": sid,
                "std_name": c.get("std_name"),
                "std_desc": d.get("std_desc"),
                "hs_code": d.get("hs_code"),
                "vector_score": c.get("score"),
                "sources": c.get("sources", []),
            }
        )

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return {"candidates": candidates, "picked_std_id": None, "reason": None}

    client = OpenAI(api_key=settings.openai_api_key)

    system = (
        "너는 수출입 거래품명 표준화 시스템의 재랭킹 모델이다.\n"
        "입력 거래품명(raw_text)과 후보 표준품명 목록(items)을 보고, 의미적으로 가장 적합한 표준품명을 고른다.\n"
        "반드시 JSON만 출력한다.\n"
        "JSON 스키마:\n"
        "{\n"
        '  "picked_std_id": number|null,\n'
        '  "reranked_std_ids": [number, ...],\n'
        '  "reason": string\n'
        "}\n"
        "- reranked_std_ids는 제공된 후보 std_id들을 가장 적합한 순서로 정렬한다.\n"
        "- 확신이 없으면 picked_std_id는 null로 둔다.\n"
        "- reason은 1~2문장.\n"
    )

    generic_rule = ""
    if generic_info.get("generic") and generic_info.get("generic_level") == "strong":
        generic_rule = (
            "중요: raw_text가 일반적/포괄적이면 단일 표준품명을 확정하면 오답 위험이 크다. "
            "이 경우 picked_std_id는 반드시 null로 두고, reason에 추가정보 필요를 명시하라."
        )

    user = {
        "raw_text": raw_text,
        "generic_input": bool(generic_info.get("generic")),
        "generic_level": generic_info.get("generic_level"),
        "generic_reason": generic_info.get("reason"),
        "items": items,
        "rules": [
            "형태/재질/공정 키워드(도금/합금/판/코일/분말/스크랩 등)가 일치하는 후보를 우선한다.",
            "std_desc와 hs_code가 있으면 의미 판단에 적극 반영한다.",
            generic_rule,
        ],
    }

    try:
        resp = client.chat.completions.create(
            model=getattr(settings, "openai_rerank_model", None) or settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.0,
            timeout=float(getattr(settings, "std_rerank_timeout_sec", 20) or 20),
        )

        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content)

        reranked_ids = data.get("reranked_std_ids") or []
        picked = data.get("picked_std_id")
        reason = data.get("reason")

        allowed = {int(x["std_id"]) for x in base}
        reranked_ids = [int(x) for x in reranked_ids if int(x) in allowed]

        if picked is not None:
            try:
                picked = int(picked)
                if picked not in allowed:
                    picked = None
            except Exception:
                picked = None

        if reranked_ids:
            by_id = {int(c["std_id"]): c for c in candidates}
            new_list = [by_id[sid] for sid in reranked_ids if sid in by_id]
            rest = [c for c in candidates if int(c["std_id"]) not in set(reranked_ids)]
            new_list.extend(rest)
            candidates = new_list

        return {"candidates": candidates, "picked_std_id": picked, "reason": reason}

    except Exception:
        return {"candidates": candidates, "picked_std_id": None, "reason": None}


# -------------------------------
# 4-2) 보류 시 follow_up_questions
# -------------------------------

def _rule_based_followups(raw_text: str, generic_info: Dict[str, Any]) -> List[str]:
    t = _normalize_text(raw_text)
    qs: List[str] = []

    if generic_info.get("generic"):
        qs.append("재질(예: 니켈/알루미늄/철강/스테인리스 등)은 무엇인가요?")
        qs.append("형상/규격(판재/코일/봉/파이프, 두께/폭 등) 정보가 있나요?")
        return qs[:2]

    if "도금" not in t and "코팅" not in t:
        qs.append("도금/코팅 등 표면처리 공정이 포함되나요? (있다면 종류)")

    if not any(x in t for x in ["니켈", "알루미늄", "구리", "철", "스테인리스", "sus", "탄소강"]):
        qs.append("주요 재질(예: 알루미늄/철강/구리/스테인리스 등)은 무엇인가요?")

    if not qs:
        qs = ["추가로 재질/공정/규격 정보를 알려주실 수 있나요?"]

    return qs[:2]


def _llm_enhance_followups(raw_text: str, base_questions: List[str]) -> List[str]:
    if not settings.openai_api_key:
        return base_questions

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return base_questions

    client = OpenAI(api_key=settings.openai_api_key)

    system = (
        "너는 수출입 거래품명 표준화 시스템의 보류(확인필요) 상황에서, 사용자에게 물어볼 후속질문을 정리한다.\n"
        "입력(raw_text)과 기본 질문(base_questions)을 받아, 더 자연스럽고 짧은 질문 1~2개로 다듬어서 JSON만 출력한다.\n"
        "JSON 스키마:\n"
        '{ "follow_up_questions": ["...", "..."] }\n'
    )

    user = {"raw_text": raw_text, "base_questions": base_questions}

    try:
        resp = client.chat.completions.create(
            model=getattr(settings, "openai_rerank_model", None) or settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.0,
            timeout=10.0,
        )
        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content)
        qs = data.get("follow_up_questions") or []
        qs = [str(x).strip() for x in qs if str(x).strip()]
        return qs[:2] if qs else base_questions
    except Exception:
        return base_questions


def normalize_std(
    raw_text: str,
    top_k: int = DEFAULT_TOPK,
    min_score: float = DEFAULT_MIN_SCORE,
    rerank: Optional[bool] = None,
    enhance_questions: bool = False,
):
    start = time.time()
    req_id = str(uuid.uuid4())

    user_topk = int(top_k or DEFAULT_TOPK)
    min_score_val = float(min_score if min_score is not None else DEFAULT_MIN_SCORE)
    retrieve_topk = max(user_topk, int(getattr(settings, "std_retrieve_topk", 30) or 30))

    generic_info = _is_generic_input(raw_text)
    neg = _is_out_of_domain(raw_text)

    # ✅ Negative Gate: 도메인 완전 무관이면 후보 자체를 비움
    if neg.get("out"):
        latency = int((time.time() - start) * 1000)

        rerank_info = {
            "enabled": bool(getattr(settings, "std_rerank_enabled", False)) if rerank is None else bool(rerank),
            "model": None,
            "picked_std_id": None,
            "reason": "입력된 거래품명이 현재 표준품명(재질/형상/공정) 도메인과 무관하여 추천할 수 없습니다.",
            "confidence": None,
            "confidence_ratio": None,
            "confidence_margin": None,
            "abstained": True,
            "abstain_reason": "NO_MATCH_OUT_OF_DOMAIN",
            "generic_input": bool(generic_info.get("generic")),
            "generic_level": generic_info.get("generic_level"),
            "generic_reason": generic_info.get("reason"),
            "negative_gate": True,
            "negative_gate_reason": neg.get("reason"),
        }

        candidates: List[Dict[str, Any]] = []
        _log_result(req_id, raw_text, candidates, latency)

        return {
            "req_id": req_id,
            "input": raw_text,
            "top_k": user_topk,
            "min_score": min_score_val,
            "retrieve_top_k": retrieve_topk,
            "recommended_hs_code": None,
            "candidates": candidates,
            "rerank": rerank_info,
            "follow_up_questions": [],  # 무관 입력은 질문 대신 '일치 없음'으로 처리
            "message": "일치되는 표준품명이 없습니다.",
            "latency_ms": latency,
        }

    master_hits = retrieve(raw_text, top_k=retrieve_topk, namespace="std_master")
    synonym_hits = retrieve(raw_text, top_k=retrieve_topk, namespace="std_synonym")

    candidates = _merge_candidates(master_hits, synonym_hits)

    # ✅ PoC 핵심: 학습 WEIGHT를 후보 점수에 반영
    _apply_weight_boost(raw_text, candidates)

    # 최소 점수 필터
    candidates = [c for c in candidates if (c.get("score") or 0) >= min_score_val]
    candidates = sorted(candidates, key=lambda x: float(x.get("score") or 0.0), reverse=True)

    # ✅ HS_CODE/STD_DESC를 candidates에 붙여 반환(환각 없음)
    detail_fetch_n = max(10, user_topk * 6)
    detail_map = _fetch_std_details([int(c["std_id"]) for c in candidates[:detail_fetch_n]])
    for c in candidates:
        d = detail_map.get(int(c["std_id"]), {})
        c["hs_code"] = d.get("hs_code")
        c["std_desc"] = d.get("std_desc")

    use_rerank = bool(getattr(settings, "std_rerank_enabled", False)) if rerank is None else bool(rerank)

    rerank_info = {
        "enabled": use_rerank,
        "model": None,
        "picked_std_id": None,
        "reason": None,
        "confidence": None,
        "confidence_ratio": None,
        "confidence_margin": None,
        "abstained": False,
        "abstain_reason": None,
        "generic_input": bool(generic_info.get("generic")),
        "generic_level": generic_info.get("generic_level"),
        "generic_reason": generic_info.get("reason"),
        "negative_gate": False,
        "negative_gate_reason": None,
    }

    # LLM rerank
    if use_rerank and len(candidates) >= 2:
        rr = _llm_rerank(raw_text, candidates, generic_info)
        candidates = rr["candidates"]
        rerank_info["model"] = getattr(settings, "openai_rerank_model", None) or settings.openai_model
        rerank_info["picked_std_id"] = rr.get("picked_std_id")
        rerank_info["reason"] = rr.get("reason")

        if rerank_info["picked_std_id"] is None:
            rerank_info["abstained"] = True
            rerank_info["abstain_reason"] = "LLM_UNCERTAIN"

    # Confidence + Abstain 정책
    abstain_enabled = bool(getattr(settings, "std_abstain_enabled", DEFAULT_ABSTAIN_ENABLED))
    confidence_min = float(getattr(settings, "std_confidence_min", DEFAULT_CONFIDENCE_MIN))
    margin_min = float(getattr(settings, "std_margin_min", DEFAULT_MARGIN_MIN))
    no2_min_score = float(getattr(settings, "std_abstain_no2_score", DEFAULT_ABSTAIN_NO2_SCORE))

    dec = _should_abstain(candidates, confidence_min, margin_min, no2_min_score)
    metrics = dec["metrics"]

    rerank_info["confidence_ratio"] = metrics.get("ratio")
    rerank_info["confidence_margin"] = metrics.get("margin")
    rerank_info["confidence"] = metrics.get("ratio")

    # 강제 보류(일반어 strong)
    generic_force_top1_min = float(getattr(settings, "std_generic_force_top1_min", DEFAULT_GENERIC_FORCE_TOP1_MIN))
    if abstain_enabled and rerank_info["generic_input"] and rerank_info.get("generic_level") == "strong":
        top1_score = float(metrics.get("top1_score") or 0.0)
        if len(candidates) >= 2 and top1_score < generic_force_top1_min:
            rerank_info["abstained"] = True
            rerank_info["abstain_reason"] = "GENERIC_INPUT_FORCE"
            rerank_info["picked_std_id"] = None

    # ratio/margin 보류
    if abstain_enabled and not rerank_info["abstained"] and dec["abstain"]:
        rerank_info["abstained"] = True
        rerank_info["abstain_reason"] = dec["reason"]
        rerank_info["picked_std_id"] = None

    if rerank_info["abstained"]:
        rerank_info["picked_std_id"] = None

    # ✅ HS_CODE 자동 추천(선택된 표준품명 기반, 환각 없음)
    recommended_hs_code = None
    if rerank_info["picked_std_id"] is not None:
        pid = int(rerank_info["picked_std_id"])
        for c in candidates:
            if int(c["std_id"]) == pid:
                recommended_hs_code = c.get("hs_code")
                break

    # ✅ 4-2: 보류 시 follow_up_questions
    follow_up_questions: List[str] = []
    if rerank_info["abstained"]:
        follow_up_questions = _rule_based_followups(raw_text, generic_info)
        if enhance_questions:
            follow_up_questions = _llm_enhance_followups(raw_text, follow_up_questions)

    candidates = candidates[:user_topk]

    latency = int((time.time() - start) * 1000)
    _log_result(req_id, raw_text, candidates, latency)

    resp = {
        "req_id": req_id,
        "input": raw_text,
        "top_k": user_topk,
        "min_score": min_score_val,
        "retrieve_top_k": retrieve_topk,
        "recommended_hs_code": recommended_hs_code,
        "candidates": candidates,
        "rerank": rerank_info,
        "follow_up_questions": follow_up_questions,
        "latency_ms": latency,
    }

    # candidates가 0이면 UI에서 "일치 없음" 문구 띄우기 쉽게 message 추가
    if not candidates:
        resp["message"] = "일치되는 표준품명이 없습니다."

    return resp


def _log_result(req_id: str, raw_text: str, candidates: List[Dict[str, Any]], latency: int):
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO TE_STD006T
                (REQ_ID, INPUT_NM, TOPK, RESULT_JSON, LATENCY_MS)
                VALUES (:req_id, :input_nm, :topk, :result_json, :latency)
            """),
            {
                "req_id": req_id,
                "input_nm": raw_text,
                "topk": len(candidates),
                "result_json": json.dumps(candidates, ensure_ascii=False),
                "latency": latency,
            },
        )


def save_feedback(req_id: str, input_nm: str, picked_std_id: int, is_correct: str):
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO TE_STD005T
                (REQ_ID, INPUT_NM, PICKED_STD_ID, IS_CORRECT)
                VALUES (:req_id, :input_nm, :picked_std_id, :is_correct)
            """),
            {
                "req_id": req_id,
                "input_nm": input_nm,
                "picked_std_id": picked_std_id,
                "is_correct": is_correct,
            },
        )