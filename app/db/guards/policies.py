from app.core.config import settings

DEFAULT_BLOCKED_KEYWORDS = [
    "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "GRANT", "REVOKE"
]

def blocked_keywords():
    if settings.allow_dml:
        return ["DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"]
    return DEFAULT_BLOCKED_KEYWORDS
