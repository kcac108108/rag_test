from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.common import SourceChunk  # ✅ 여기만 쓰면 클래스 충돌 안 남


class SQLQueryRequest(BaseModel):
    question: str = Field(..., description="자연어 질문")

    top_k: int = Field(5, ge=1, le=20, description="RAG 검색 문서 개수")

    row_limit: int = Field(200, ge=1, le=10000, description="결과 최대 행 수")
    dialect: Optional[str] = Field(None, description="oracle | postgres (None이면 서버 기본값)")
    dry_run: bool = Field(False, description="true면 SQL만 생성하고 실행하지 않음")

    include_sources: bool = Field(False, description="sources 포함 여부(토큰 절약)")
    include_total: bool = Field(False, description="total_rows 계산 여부(count 쿼리 1회 추가)")


class SQLQueryResponse(BaseModel):
    sql: str = Field(..., description="최종 SQL")
    summary: str = Field(..., description="요약")

    results: List[Dict[str, Any]] = Field(default_factory=list, description="결과 rows")

    total_rows: Optional[int] = Field(None, description="LIMIT 적용 전 전체 건수(include_total=true일 때)")
    is_limited: bool = Field(False, description="row_limit 때문에 잘렸는지 여부")

    sources: Optional[List[SourceChunk]] = Field(None, description="RAG sources(include_sources=true일 때)")
    warnings: List[str] = Field(default_factory=list, description="경고 메시지")
