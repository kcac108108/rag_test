from typing import Any, Dict, List, Tuple

def format_rows(rows: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    if not rows:
        return "No rows returned.", []
    return f"Returned {len(rows)} row(s).", rows
