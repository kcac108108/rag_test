# app/text_to_sql/prompts.py
from __future__ import annotations


def sql_system_prompt(dialect: str = "postgres") -> str:
    d = (dialect or "postgres").lower().strip()

    base_rules = (
        "You are an expert data analyst who writes correct, safe, read-only SQL.\n"
        "You must output ONLY SQL (no markdown, no explanations, no code fences).\n"
        "Do not use DML/DDL: INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, TRUNCATE, CREATE.\n"
        "If the user asks to modify data or schema, do NOT generate DML/DDL.\n"
        "This service is strictly read-only. For write-intent questions, return a harmless read-only SQL such as SELECT 1 AS example.\n"
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
        "- Prefer readable aliases for tables (e.g., T, M, H).\n"
        "\n"
        "SUBQUERY / INLINE VIEW ALIAS SCOPE RULE (CRITICAL):\n"
        "- If you use a subquery or inline view in FROM ( ... ), you MUST assign it an alias, e.g. FROM ( ... ) A.\n"
        "- Table aliases defined INSIDE a subquery (such as T, M, H) are NOT visible in the OUTER query.\n"
        "- In the outer SELECT / GROUP BY / ORDER BY, NEVER reference inner aliases like T.COL.\n"
        "- In the outer query, use ONLY the inline-view alias (e.g. A.COL) or exposed column names.\n"
        "- For monthly-average patterns, prefer:\n"
        "  SELECT SUBSTR(A.ACPT_YYMM, 5, 2), AVG(A.MONTH_SUM)\n"
        "  FROM ( ... ) A\n"
        "  GROUP BY SUBSTR(A.ACPT_YYMM, 5, 2)\n"
        "\n"
        "GROWTH RATE / CHANGE RATE RULE (CRITICAL):\n"
        "- If the question asks about 증감률, 증가율, 감소율, 전년대비, 전년동기대비, YOY, growth rate, change rate:\n"
        "- NEVER divide directly by a previous-period value without zero protection.\n"
        "- Use NULLIF(previous_value, 0) in the denominator OR filter previous_value > 0.\n"
        "- If ranking or sorting by the rate, exclude rows whose base(previous period) is NULL or 0 whenever the question is about 순위, N위, 상위, TOP N.\n"
        "- In Oracle, if ordering by a nullable growth-rate expression, use NULLS LAST.\n"
        "- Prefer this formula: ((current_value - previous_value) / NULLIF(previous_value, 0)) * 100.\n"
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
              "- If ranking by 증감률, use ORDER BY growth_rate DESC NULLS LAST.\n"
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
        "- If the question requests data/schema modification (e.g. update, delete, create, alter, drop), do NOT generate DML/DDL.\n"
        "- For read-only fallback, return a harmless SELECT such as SELECT 1 AS example.\n"
        "- If you use a subquery in FROM, you MUST assign an alias to the subquery.\n"
        "- Never reference inner table aliases from the outer query. Use only the subquery alias in the outer query.\n"
        "- For 증감률 / 증가율 / 감소율 / 전년대비 / 전년동기대비 questions, protect against division by zero with NULLIF or previous-value filtering.\n"
        "- For 순위 / N위 / 상위 questions on 증감률, do not allow NULL growth-rate rows to rank above valid rows. Use previous-value filtering and NULLS LAST when needed.\n"
    )