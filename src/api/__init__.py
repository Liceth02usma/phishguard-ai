"""API REST de PhishGuard-AI (spec 012, M14).

Public API:
    create_app — FastAPI application factory
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
