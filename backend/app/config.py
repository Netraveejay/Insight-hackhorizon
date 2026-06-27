from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./insight.db"
    openai_api_key: str = ""
    rules_path: str = "rules/rules.v1.yaml"
    teams_webhook_url: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    auth_secret: str = "insight-demo-secret-change-in-production"
    reports_dir: str = "data/reports"
    feedback_file_path: str = ""
    auto_seed: bool = True
    enable_scheduler: bool = True
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_reports_path(self) -> Path:
        p = Path(self.reports_dir)
        if p.is_absolute():
            return p
        return Path.cwd() / p

    @property
    def resolved_rules_path(self) -> Path:
        p = Path(self.rules_path)
        if p.is_absolute():
            return p
        # Try relative to backend, then insight root
        for base in [Path.cwd(), Path.cwd().parent, Path(__file__).resolve().parent.parent.parent]:
            candidate = base / self.rules_path
            if candidate.exists():
                return candidate
        return Path(self.rules_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
