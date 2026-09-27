"""Vercel serverless entry point.

Re-exports the existing FastAPI application from ``backend/app/main.py`` —
this is NOT a second app, just the deploy adapter so ``/api/*`` rewrites
reach the same routers, models, and behavior as local development.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402  (import after sys.path setup)

# The Vercel Python runtime serves this ASGI ``app``.
__all__ = ["app"]
