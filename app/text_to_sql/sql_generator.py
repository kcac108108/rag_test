from app.core.config import settings
from app.text_to_sql.prompts import sql_system_prompt, build_user_prompt


def generate_sql(question: str, context: str, dialect: str, row_limit: int) -> str:
    # If no key, return a placeholder SQL so the server still works.
    if not settings.openai_api_key:
        return "SELECT 1 AS example;"

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    system_prompt = sql_system_prompt(dialect=dialect)
    user_prompt = build_user_prompt(
        question=question,
        context=context,
        dialect=dialect,
        row_limit=row_limit,
    )

    resp = llm.invoke([("system", system_prompt), ("user", user_prompt)])
    return (resp.content or "").strip()
