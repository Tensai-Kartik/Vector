import sys
import os
import asyncio
from pathlib import Path

# Set up project root and backend path
project_root = Path(__file__).resolve().parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure WindowsProactorEventLoopPolicy is active for Playwright Chromium
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        import uvicorn.loops.asyncio
        uvicorn.loops.asyncio.asyncio_setup = lambda use_subprocess=False: None
    except Exception:
        pass

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting VECTOR backend on {settings.HOST}:{settings.PORT} ...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_dirs=[str(backend_dir)],
        reload_excludes=["*.db*", "*.sqlite*", "*.journal*", "*.wal*", "data/*", "*.log", "data/**/*"],
        app_dir=str(backend_dir)
    )

