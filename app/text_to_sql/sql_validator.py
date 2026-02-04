import re
from typing import List, Tuple
from app.db.guards.policies import blocked_keywords

def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql

def validate_sql(sql: str) -> Tuple[bool, List[str]]:
    if not sql or not sql.strip():
        return False, ["Empty SQL generated"]

    cleaned = _strip_comments(sql).strip()
    upper = cleaned.upper()

    if not re.match(r"^(SELECT|WITH)\b", upper):
        return False, ["Only SELECT/WITH queries are allowed"]

    for kw in blocked_keywords():
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            return False, [f"Blocked keyword detected: {kw}"]

    # multi-statement guard (allow trailing ;)
    core = cleaned.rstrip().rstrip(";")
    if ";" in core:
        return False, ["Multiple statements are not allowed"]

    return True, []
