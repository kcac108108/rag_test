# app/text_to_sql/prompts.py

from __future__ import annotations

from typing import List, Dict


def sql_system_prompt(dialect: str = "postgres") -> str:
    """
    dialect: "oracle" | "postgres" 등
    """
    d = (dialect or "postgres").lower().strip()

    base_rules = (
        "You are an expert data analyst who writes correct, safe, read-only SQL.\n"
        "You must output ONLY SQL (no markdown, no explanations).\n"
        "Do not use DML/DDL: INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, TRUNCATE, CREATE.\n"
        "Use only the tables/columns provided in the context.\n"
        "If the question is ambiguous, choose the most reasonable interpretation using the provided schema.\n"
        "\n"
        "Ranking rules (VERY IMPORTANT):\n"
        "- If the user asks for a single rank like '2위', '3위', 'N위':\n"
        "  - This means the N-th rank ONLY (NOT 'top N').\n"
        "  - Return ONLY rows whose rank is exactly N.\n"
        "  - Include ties for that rank.\n"
        "  - Use competition ranking (ties share the same rank and next rank is skipped): use RANK().\n"
        "  - Do NOT add tie-breaker columns inside the RANK() ORDER BY (it breaks ties).\n"
        "  - You may add ORDER BY for display AFTER filtering by rank.\n"
        "- If the user asks for '상위 N개' / 'top N', return N rows.\n"
        "\n"
        "Row limiting rules:\n"
        "- Apply row limiting clause exactly once.\n"
        "- Never output both LIMIT and FETCH FIRST in the same SQL.\n"
        "- Never duplicate row limiting clauses.\n"
    )

    if d == "oracle":
        return (
            base_rules
            + "Target database: Oracle.\n"
              "Oracle rules:\n"
              "- DO NOT use LIMIT.\n"
              "- Use 'FETCH FIRST N ROWS ONLY' to limit rows.\n"
              "- Prefer VARCHAR2 for string casting if needed.\n"
        )

    # default: postgres
    return (
        base_rules
        + "Target database: PostgreSQL.\n"
          "PostgreSQL rules:\n"
          "- You may use LIMIT N to limit rows.\n"
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
        f"Write ONE SQL query. {limit_hint}\n"
    )
