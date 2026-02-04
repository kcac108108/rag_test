from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -----------------
    # LLM
    # -----------------
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")

    # -----------------
    # Chroma
    # -----------------
    chroma_dir: str = Field(default="./chroma_db", validation_alias="CHROMA_DIR")
    chroma_collection: str = Field(default="rag_sql", validation_alias="CHROMA_COLLECTION")

    # -----------------
    # DB (Postgres)
    # -----------------
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    db_dialect: str = Field(default="postgres", validation_alias="DB_DIALECT")

    # -----------------
    # DB (Oracle)  ✅ 추가
    # oracle connector(app/db/connectors/oracle.py)가 이 필드들을 찾습니다.
    # -----------------
    oracle_dsn: str = Field(default="", validation_alias="ORACLE_DSN")
    oracle_user: str = Field(default="", validation_alias="ORACLE_USER")
    oracle_password: str = Field(default="", validation_alias="ORACLE_PASSWORD")

    # -----------------
    # Safety / limits
    # -----------------
    max_rows: int = Field(default=200, validation_alias="MAX_ROWS")
    statement_timeout_sec: int = Field(default=15, validation_alias="STATEMENT_TIMEOUT_SEC")
    allow_dml: bool = Field(default=False, validation_alias="ALLOW_DML")

    admin_reset_token: str = Field(default="", validation_alias="ADMIN_RESET_TOKEN")


settings = Settings()
