from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # 'mock' or 'gemini'
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # API Integrations
    GITHUB_TOKEN: str = ""

    # Browser Automation Settings
    BROWSER_HEADLESS: bool = True
    BROWSER_SLOWMO_MS: int = 100
    SCREENSHOT_STREAM_INTERVAL_MS: int = 300
    MAX_MISSION_TIMEOUT_SECONDS: int = 180
    MAX_STEP_RETRIES: int = 2
    MAX_DOWNLOAD_SIZE_BYTES: int = 10485760  # 10 MB limit

    # Guardrail Allowlist
    ALLOWED_DOMAINS: str = "localhost,127.0.0.1,api.github.com,github.com"

    # File & Database paths
    DATABASE_URL: str = "sqlite:///./data/vector.db"
    ARTIFACTS_DIR: str = "./data/artifacts"

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_domains_list(self) -> List[str]:
        if not self.ALLOWED_DOMAINS:
            return []
        return [d.strip().lower() for d in self.ALLOWED_DOMAINS.split(",") if d.strip()]

    @property
    def absolute_db_path(self) -> Path:
        raw = self.DATABASE_URL.replace("sqlite:///", "")
        p = Path(raw)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def absolute_artifacts_dir(self) -> Path:
        p = Path(self.ARTIFACTS_DIR)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
