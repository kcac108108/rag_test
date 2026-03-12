from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.sql import SQLQueryRequest, SQLQueryResponse
from app.services.sql_service import SQLService
import io
import csv
from datetime import datetime

router = APIRouter()
service = SQLService()


@router.post("/query", response_model=SQLQueryResponse)
def query(req: SQLQueryRequest):
    return service.handle(req)


# ----------------------------
# CSV Export API
# ----------------------------
@router.post("/export/csv")
def export_csv(req: SQLQueryRequest):

    result = service.handle(req)

    rows = result.results or []

    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        headers = list(rows[0].keys())
        writer.writerow(headers)

        for r in rows:
            writer.writerow([r.get(h, "") for h in headers])

    output.seek(0)

    filename = "sql_result_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )