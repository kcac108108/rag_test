from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.std_service import normalize_std, save_feedback

router = APIRouter(prefix="/std", tags=["std"])


class NormalizeRequest(BaseModel):
    raw_text: str
    top_k: Optional[int] = 5
    min_score: Optional[float] = 0.8
    rerank: Optional[bool] = None
    enhance_questions: Optional[bool] = False


class FeedbackRequest(BaseModel):
    req_id: str
    input_nm: str
    picked_std_id: int
    is_correct: str


@router.post("/normalize")
def normalize(req: NormalizeRequest):
    return normalize_std(
        raw_text=req.raw_text,
        top_k=req.top_k,
        min_score=req.min_score,
        rerank=req.rerank,
        enhance_questions=bool(req.enhance_questions),
    )


@router.post("/feedback")
def feedback(req: FeedbackRequest):
    save_feedback(
        req_id=req.req_id,
        input_nm=req.input_nm,
        picked_std_id=req.picked_std_id,
        is_correct=req.is_correct,
    )
    return {"status": "ok"}