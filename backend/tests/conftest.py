import pytest
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database.db import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    settings.LLM_PROVIDER = "mock"
    settings.DATABASE_URL = "sqlite:///:memory:"
    init_db()
    settings.absolute_artifacts_dir.mkdir(parents=True, exist_ok=True)
    yield
