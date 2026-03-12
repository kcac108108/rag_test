from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")

    # std rerank
    std_rerank_enabled: bool = Field(default=False, validation_alias="STD_RERANK_ENABLED")
    openai_rerank_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_RERANK_MODEL")
    std_rerank_topn: int = Field(default=12, validation_alias="STD_RERANK_TOPN")  # 정확도 모드 기본 12
    std_rerank_timeout_sec: int = Field(default=20, validation_alias="STD_RERANK_TIMEOUT_SEC")

    # 정확도 2단계: 내부 벡터 후보수(Recall)
    std_retrieve_topk: int = Field(default=30, validation_alias="STD_RETRIEVE_TOPK")

    # ✅ Abstain 정책(룰)
    std_abstain_enabled: bool = Field(default=True, validation_alias="STD_ABSTAIN_ENABLED")
    std_confidence_min: float = Field(default=1.15, validation_alias="STD_CONFIDENCE_MIN")  # ratio 최소
    std_margin_min: float = Field(default=0.15, validation_alias="STD_MARGIN_MIN")          # margin 최소
    std_abstain_no2_score: float = Field(default=1.0, validation_alias="STD_ABSTAIN_NO2_SCORE")
    std_generic_force_top1_min: float = Field(default=2.8, validation_alias="STD_GENERIC_FORCE_TOP1_MIN")

    # ✅ confidence_norm (0~1) 정규화 설정
    std_conf_norm_ratio_low: float = Field(default=1.0, validation_alias="STD_CONF_NORM_RATIO_LOW")
    std_conf_norm_ratio_high: float = Field(default=2.5, validation_alias="STD_CONF_NORM_RATIO_HIGH")

    std_conf_norm_margin_low: float = Field(default=0.0, validation_alias="STD_CONF_NORM_MARGIN_LOW")
    std_conf_norm_margin_high: float = Field(default=2.0, validation_alias="STD_CONF_NORM_MARGIN_HIGH")

    # 단일 후보일 때 top1 score 정규화 범위
    std_conf_norm_single_score_low: float = Field(default=1.0, validation_alias="STD_CONF_NORM_SINGLE_SCORE_LOW")
    std_conf_norm_single_score_high: float = Field(default=3.0, validation_alias="STD_CONF_NORM_SINGLE_SCORE_HIGH")

    # ratio/margin 가중치(합이 1일 필요는 없음)
    std_conf_norm_weight_ratio: float = Field(default=0.65, validation_alias="STD_CONF_NORM_WEIGHT_RATIO")
    std_conf_norm_weight_margin: float = Field(default=0.35, validation_alias="STD_CONF_NORM_WEIGHT_MARGIN")

    # ✅ confidence_level 임계값
    std_conf_level_high: float = Field(default=0.75, validation_alias="STD_CONF_LEVEL_HIGH")
    std_conf_level_medium: float = Field(default=0.45, validation_alias="STD_CONF_LEVEL_MEDIUM")

    # Chroma
    chroma_dir: str = Field(default="./chroma_db", validation_alias="CHROMA_DIR")
    chroma_collection: str = Field(default="rag_sql", validation_alias="CHROMA_COLLECTION")

    # DB (Postgres)
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    db_dialect: str = Field(default="postgres", validation_alias="DB_DIALECT")

    # DB (Oracle)
    oracle_dsn: str = Field(default="", validation_alias="ORACLE_DSN")
    oracle_user: str = Field(default="", validation_alias="ORACLE_USER")
    oracle_password: str = Field(default="", validation_alias="ORACLE_PASSWORD")

    # limits
    max_rows: int = Field(default=200, validation_alias="MAX_ROWS")
    statement_timeout_sec: int = Field(default=15, validation_alias="STATEMENT_TIMEOUT_SEC")
    allow_dml: bool = Field(default=False, validation_alias="ALLOW_DML")

    admin_reset_token: str = Field(default="", validation_alias="ADMIN_RESET_TOKEN")


settings = Settings()