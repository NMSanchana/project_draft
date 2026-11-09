"""Application settings, read from environment variables / ``ai-service/.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # .../ai-service


def _abs(path: str) -> Path:
    """Resolve a (possibly relative) path against the ai-service directory."""
    p = Path(path)
    return p if p.is_absolute() else (BASE_DIR / p).resolve()


class Settings(BaseSettings):
    """Runtime configuration. Every value has a safe local default except JWT_SECRET."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    jwt_secret: str = Field(default="", description="Must equal Nest/Next JWT_SECRET")
    jwt_algorithm: str = "HS256"
    database_url: str = "sqlite:///./data/ai_service.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    qdrant_url: str = "http://localhost:6333"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    upload_dir: str = "./data/uploads"
    kb_dir: str = "./knowledge_base"
    max_upload_mb: int = 10
    log_level: str = "INFO"
    kb_autosync: bool = True  # watch knowledge_base/ and ingest changes in the background

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        return _abs(self.upload_dir)

    @property
    def kb_path(self) -> Path:
        return _abs(self.kb_dir)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def sqlalchemy_url(self) -> str:
        """Make relative sqlite paths independent of the process working directory."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix) and not self.database_url.startswith("sqlite:////"):
            rel = self.database_url[len(prefix) :]
            if rel != ":memory:" and not rel.startswith("file:"):
                return prefix + str(_abs(rel))
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
