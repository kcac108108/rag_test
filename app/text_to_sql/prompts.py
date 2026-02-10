# app/text_to_sql/prompts.py
from __future__ import annotations

def sql_system_prompt(dialect: str = "postgres") -> str:
    d = (dialect or "postgres").lower().strip()

    base_rules = (
        "You are an expert data analyst who writes correct, safe, read-only SQL.\n"
        "You must output ONLY SQL (no markdown, no explanations, no code fences).\n"
        "Do not use DML/DDL: INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, TRUNCATE, CREATE.\n"
        "Use only the tables/columns provided in the context.\n"
        "If the question is ambiguous, choose the most reasonable interpretation using the provided schema.\n"
        "\n"
        "OUTPUT COLUMN ALIAS RULE (CRITICAL):\n"
        "- Every output column in the FINAL SELECT must have a Korean alias suitable for table headers.\n"
        "- Do NOT leave raw column names like CNTY_NM; it must be aliased, e.g. CNTY_NM AS \"국가명\".\n"
        "- Do NOT use SELECT *.\n"
        "- Never duplicate aliases (no 'AS X AS X').\n"
        "\n"
        "JOIN RULE:\n"
        "- If a code table exists (e.g., country code -> country name), join it to show the Korean name.\n"
        "- Prefer readable aliases for tables (e.g., T, M).\n"
    )

    if d == "oracle":
        return (
            base_rules
            + "Target database: Oracle.\n"
              "Oracle rules:\n"
              "- DO NOT use LIMIT.\n"
              "- Use 'FETCH FIRST N ROWS ONLY' to limit rows.\n"
              "- For Korean aliases, ALWAYS use double quotes: AS \"한글별칭\".\n"
              "- Analytic/window functions cannot be used directly in WHERE/HAVING; use a subquery/CTE then filter outside.\n"
        )

    return (
        base_rules
        + "Target database: PostgreSQL.\n"
          "PostgreSQL rules:\n"
          "- You may use LIMIT N to limit rows.\n"
          "- For Korean aliases, use double quotes as well: AS \"한글별칭\".\n"
    )


def build_user_prompt(
    question: str,
    context: str,
    row_limit: int = 200,
    dialect: str = "postgres",
) -> str:
    d = (dialect or "postgres").lower().strip()
    limit_hint = (
        f"Use FETCH FIRST {row_limit} ROWS ONLY."
        if d == "oracle"
        else f"Use LIMIT {row_limit}."
    )

    return (
        "### Context\n"
        f"{context}\n\n"
        "### Question\n"
        f"{question}\n\n"
        "### Output\n"
        "Write ONE SQL query.\n"
        f"{limit_hint}\n"
        "\n"
        "CRITICAL OUTPUT FORMAT:\n"
        "- Output ONLY SQL.\n"
        "- FINAL SELECT must provide Korean aliases for every output column.\n"
        "- In Oracle, Korean aliases MUST be double-quoted: AS \"한글\".\n"
    )
