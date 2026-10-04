from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://nl2sql:nl2sql@localhost:5432/nl2sql_demo"
    app_database_url: str = "postgresql+psycopg://querydesk:querydesk@localhost:5433/querydesk_app"
    schema_path: Path = ROOT / "SCHEMA.md"
    model_provider: str = "google_genai"
    model_name: str = "gemini-3.8-flash"
    model_api_key: str = ""
    google_api_key: str = ""
    model_base_url: str = ""
    model_temperature: float = 0.0
    max_result_rows: int = Field(default=500, ge=1, le=10000)
    query_timeout_ms: int = Field(default=8000, ge=100, le=120000)
    keycloak_issuer: str = "http://localhost:8081/realms/querydesk"
    keycloak_jwks_url: str = "http://keycloak:8080/realms/querydesk/protocol/openid-connect/certs"
    keycloak_audience: str = "querydesk-api"


@lru_cache
def get_settings() -> Settings:
    return Settings()
