from pydantic import BaseModel, Field
from typing import List, Optional

class IngestSchemaRequest(BaseModel):
    file_path: Optional[str] = None  # if omitted, ingest from data/schema directory
    namespace: str = "schema"

class IngestExamplesRequest(BaseModel):
    file_path: Optional[str] = None  # if omitted, ingest from data/examples directory
    namespace: str = "examples"

class IngestResponse(BaseModel):
    added: int
    namespace: str
    ids: List[str] = Field(default_factory=list)
