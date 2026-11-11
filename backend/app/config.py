from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os
import sys
from pathlib import Path

# Dynamically resolve repository root whether running from repo root or inside backend/
_file_path = Path(__file__).resolve()
if (_file_path.parent.parent.parent / "backend").exists():
    BASE_DIR = _file_path.parent.parent.parent
elif (_file_path.parent.parent / "app").exists():
    BASE_DIR = _file_path.parent.parent
else:
    BASE_DIR = Path.cwd()

class Settings(BaseSettings):
    # Server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # Planning & LLM Settings:
    # Default working planner is always 'deterministic' unless explicitly switched or deterministic fails.
    # LLM_PROVIDER='gemini' configures the cloud LLM standby/optional engine when GEMINI_API_KEY is present.
    PLANNER_MODE: str = "deterministic"
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # API Integrations
    GITHUB_TOKEN: str = ""

    # Browser Automation Settings (Default False on Windows desktop; True on cloud/Linux/Render)
    BROWSER_HEADLESS: bool = False if (sys.platform == "win32" and not os.getenv("RENDER")) else True
    BROWSER_SLOWMO_MS: int = 0
    SCREENSHOT_STREAM_INTERVAL_MS: int = 800
    MAX_MISSION_TIMEOUT_SECONDS: int = 180
    MAX_STEP_RETRIES: int = 2
    MAX_DOWNLOAD_SIZE_BYTES: int = 10485760  # 10 MB limit

    # Guardrail Allowlist
    ALLOWED_DOMAINS: str = "localhost,127.0.0.1,api.github.com,github.com,*"

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
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Verify directory is writable
            test_probe = p.parent / ".write_test"
            test_probe.touch()
            test_probe.unlink()
            return p
        except Exception:
            # Safe writable fallback within project directory or system temp
            try:
                fallback = BASE_DIR / "data" / "vector.db"
                fallback.parent.mkdir(parents=True, exist_ok=True)
                return fallback
            except Exception:
                import tempfile
                tmp_dir = Path(tempfile.gettempdir()) / "vector_data"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                return tmp_dir / "vector.db"

    @property
    def absolute_artifacts_dir(self) -> Path:
        p = Path(self.ARTIFACTS_DIR)
        if not p.is_absolute():
            p = BASE_DIR / p
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            try:
                fallback = BASE_DIR / "data" / "artifacts"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback
            except Exception:
                import tempfile
                tmp_dir = Path(tempfile.gettempdir()) / "vector_artifacts"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                return tmp_dir

settings = Settings()
