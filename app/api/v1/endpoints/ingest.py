import os
from pathlib import Path

from fastapi import APIRouter
from app.schemas.ingest import IngestSchemaRequest, IngestExamplesRequest, IngestResponse
from app.services.ingest_service import ingest_namespace

router = APIRouter()

@router.post("/schema", response_model=IngestResponse)
def ingest_schema(req: IngestSchemaRequest):
    print("CWD:", os.getcwd())
    print("EXPECTED:", str(Path(os.getcwd()) / "data" / "schema"))
    added, ids = ingest_namespace("schema", file_path=req.file_path)
    return IngestResponse(added=added, namespace=req.namespace, ids=ids)

@router.post("/examples", response_model=IngestResponse)
def ingest_examples(req: IngestExamplesRequest):
    added, ids = ingest_namespace("examples", file_path=req.file_path)
    return IngestResponse(added=added, namespace=req.namespace, ids=ids)
