from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.std_synonym_service import (
    approve_synonym_suggestion,
    reject_synonym_suggestion,
    list_synonym_suggestions,
    generate_synonym_suggestions,
    batch_approve_synonym_suggestions,
    batch_reject_synonym_suggestions,
)

router = APIRouter(prefix="/std-admin", tags=["std-admin"])


@router.post("/generate-synonym-suggestions")
def generate():
    return generate_synonym_suggestions()


class ApproveSuggestionRequest(BaseModel):
    sug_id: int = Field(..., description="TE_STD007T의 제안 ID(SUG_ID)")
    reindex: bool = Field(True, description="승인 후 Chroma 증분 재인덱싱 여부")


class ApproveSuggestionResponse(BaseModel):
    ok: bool
    sug_id: int
    std_id: int | None = None
    synonym: str | None = None
    weight: float | None = None
    prev_status: str | None = None
    approved: bool | None = None
    inserted_to_std002l: bool | None = None
    syn_id: int | None = None
    reindexed: bool | None = None
    error: str | None = None


@router.post("/approve-synonym-suggestion", response_model=ApproveSuggestionResponse)
def approve(req: ApproveSuggestionRequest):
    return approve_synonym_suggestion(req.sug_id, reindex=req.reindex)


class RejectSuggestionRequest(BaseModel):
    sug_id: int = Field(..., description="TE_STD007T의 제안 ID(SUG_ID)")
    reason: str | None = Field(None, description="거절 사유(TE_STD007T.REJECT_REASON 저장)")


class RejectSuggestionResponse(BaseModel):
    ok: bool
    sug_id: int
    rejected: bool | None = None
    prev_status: str | None = None
    reason: str | None = None
    error: str | None = None


@router.post("/reject-synonym-suggestion", response_model=RejectSuggestionResponse)
def reject(req: RejectSuggestionRequest):
    return reject_synonym_suggestion(req.sug_id, reason=req.reason)


class SuggestionItem(BaseModel):
    sug_id: int
    std_id: int
    std_name: str | None = None
    input_nm: str | None = None
    sug_weight: float | None = None
    status: str | None = None
    source_type: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    reject_reason: str | None = None


class SuggestionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SuggestionItem]


@router.get("/suggestions", response_model=SuggestionListResponse)
def suggestions(
    status: str = Query("P", description="P/A/R/ALL"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    std_id: int | None = Query(None),
    q: str | None = Query(None, description="입력명/표준품명 부분검색"),
):
    return list_synonym_suggestions(status=status, limit=limit, offset=offset, std_id=std_id, q=q)


@router.get("/pending-suggestions", response_model=SuggestionListResponse)
def pending_suggestions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    std_id: int | None = Query(None),
    q: str | None = Query(None),
):
    return list_synonym_suggestions(status="P", limit=limit, offset=offset, std_id=std_id, q=q)


# -----------------------------
# Batch APIs
# -----------------------------
class BatchApproveRequest(BaseModel):
    sug_ids: list[int] = Field(..., min_length=1, description="승인할 SUG_ID 목록")
    reindex: bool = Field(True, description="승인 완료 후 Chroma 증분 재인덱싱(가능하면) 수행")


class BatchApproveResponse(BaseModel):
    ok: bool
    requested: int
    approved_ok: int
    errors: int
    reindexed_count: int
    results: list[ApproveSuggestionResponse]


@router.post("/batch-approve-synonym-suggestions", response_model=BatchApproveResponse)
def batch_approve(req: BatchApproveRequest):
    return batch_approve_synonym_suggestions(req.sug_ids, reindex=req.reindex)


class BatchRejectItem(BaseModel):
    sug_id: int = Field(..., description="거절할 SUG_ID")
    reason: str | None = Field(None, description="거절 사유(선택)")


class BatchRejectRequest(BaseModel):
    items: list[BatchRejectItem] = Field(..., min_length=1, description="거절 항목 리스트")


class BatchRejectResponse(BaseModel):
    ok: bool
    requested: int
    rejected_ok: int
    errors: int
    results: list[RejectSuggestionResponse]


@router.post("/batch-reject-synonym-suggestions", response_model=BatchRejectResponse)
def batch_reject(req: BatchRejectRequest):
    items = [{"sug_id": x.sug_id, "reason": x.reason} for x in req.items]
    return batch_reject_synonym_suggestions(items)