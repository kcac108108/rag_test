# app/text_to_sql/context_builder.py
from typing import List, Tuple

from app.rag.retriever import retrieve
from app.schemas.common import SourceChunk


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

5. Growth-rate / change-rate rule (MANDATORY):
   If the question asks for 증감률, 증가율, 감소율, 전년대비, 전년동기대비, then:
   - NEVER divide directly by a previous-period metric without zero protection.
   - Use NULLIF(previous_value, 0) in the denominator, OR filter previous_value > 0.
   - If ranking or sorting by the calculated rate, use NULLS LAST in Oracle.
   - Prefer excluding rows where the base(previous period) is NULL or 0 when the question asks for 순위 / 상위 / N위.

6. Correct growth-rate pattern (MANDATORY):

WITH base AS (
    ...
),
calc AS (
    SELECT
        ...,
        ((curr_value - prev_value) / NULLIF(prev_value, 0)) * 100 AS growth_rate
    FROM base
),
ranked AS (
    SELECT
        ...,
        growth_rate,
        RANK() OVER (ORDER BY growth_rate DESC NULLS LAST) AS rnk
    FROM calc
    WHERE prev_value > 0
)
SELECT ...
FROM ranked
WHERE rnk = <N>;

These rules are mandatory and violations will cause execution failure or wrong ranking.
"""


def build_context(question: str, top_k: int) -> Tuple[str, List[SourceChunk]]:
    schema_chunks = retrieve(question, top_k=top_k, namespace="schema")
    example_chunks = retrieve(question, top_k=max(2, top_k // 2), namespace="examples")

    def format_chunks(title: str, chunks: List[SourceChunk]) -> str:
        if not chunks:
            return f"{title}: (none)\n"

        lines = [f"{title}:"]
        for chunk in chunks:
            lines.append(f"- {chunk.text.strip()}")
        return "\n".join(lines) + "\n"

    context = "\n".join(
        [
            format_chunks("Relevant schema", schema_chunks),
            format_chunks("Relevant examples", example_chunks),
            _CRITICAL_SQL_RULES,
        ]
    ).strip()

    return context, schema_chunks + example_chunks