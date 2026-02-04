from fastapi import APIRouter
from app.schemas.sql import SQLQueryRequest, SQLQueryResponse
from app.services.sql_service import SQLService

router = APIRouter()
service = SQLService()

@router.post("/query", response_model=SQLQueryResponse)
def query(req: SQLQueryRequest):
    return service.handle(req)
