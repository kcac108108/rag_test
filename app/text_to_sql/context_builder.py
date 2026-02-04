# app/text_to_sql/context_builder.py
from typing import List, Tuple
from app.schemas.common import SourceChunk
from app.rag.retriever import retrieve

_CRITICAL_SQL_RULES = """
[CRITICAL ORACLE SQL RULES - MUST FOLLOW]

1. NEVER use analytic/window functions such as RANK(), DENSE_RANK(), ROW_NUMBER()
   directly in WHERE or HAVING clauses in Oracle.

2. If the question asks for a specific rank (e.g. "2위", "두번째", "rank 3"),
   you MUST use a subquery or CTE.

3. Correct pattern (MANDATORY):

WITH ranked AS (
    SELECT
        <group columns>,
        <aggregates> AS total_metric,
        RANK() OVER (ORDER BY <aggregates> DESC) AS rnk
    FROM <table>
    WHERE <conditions>
    GROUP BY <group columns>
)
SELECT <group columns>, total_metric
FROM ranked
WHERE rnk = <N>;

4. Incorrect pattern (NEVER USE):

SELECT ...
FROM ...
GROUP BY ...
HAVING RANK() OVER (...) = N;

This rule is mandatory and violations will cause execution failure.
"""

def build_context(question: str, top_k: int) -> Tuple[str, List[SourceChunk]]:
    schema_chunks = retrieve(question, top_k=top_k, namespace="schema")
    example_chunks = retrieve(question, top_k=max(2, top_k // 2), namespace="examples")

    def format_chunks(title: str, chunks: List[SourceChunk]) -> str:
        if not chunks:
            return f"{title}: (none)\n"
        lines = [f"{title}:"]
        for c in chunks:
            lines.append(f"- {c.text.strip()}")
        return "\n".join(lines) + "\n"

    context = "\n".join([
        format_chunks("Relevant schema", schema_chunks),
        format_chunks("Relevant examples", example_chunks),
        _CRITICAL_SQL_RULES,
    ]).strip()

    return context, schema_chunks + example_chunks
