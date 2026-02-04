from pydantic import BaseModel, Field
from typing import Any, Dict

class SourceChunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
