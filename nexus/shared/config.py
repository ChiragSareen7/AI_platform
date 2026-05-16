from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nexus_env: str = "development"
    nexus_log_level: str = "INFO"

    nexus_gateway_host: str = "0.0.0.0"
    nexus_gateway_port: int = 8090
    nexus_governance_host: str = "0.0.0.0"
    nexus_governance_port: int = 8091

    database_url: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 120

    models_api_base: str = "http://127.0.0.1:8010"
    ai_agent_base: str = "http://127.0.0.1:8000"
    deterministic_base: str = "http://127.0.0.1:3002"
    platform_base: str = "http://127.0.0.1:3001"
    multi_model_base: str = "http://127.0.0.1:8020"

    nexus_score_w_accuracy: float = 0.25
    nexus_score_w_hallucination: float = 0.20
    nexus_score_w_relevance: float = 0.20
    nexus_score_w_groundedness: float = 0.20
    nexus_score_w_confidence: float = 0.10
    nexus_score_w_latency: float = 0.05


settings = Settings()

