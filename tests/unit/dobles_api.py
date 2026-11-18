"""Dobles de prueba para la API REST (spec 012).

Usa TestClient de FastAPI con repositorios in-memory.
"""

from __future__ import annotations

import os

from httpx import ASGITransport, AsyncClient
from src.api.app import create_app
from src.api.persistence_repos import CacheVTDoble, RepositorioAnalisisDoble


def _set_test_api_key() -> None:
    """Configura API_KEY para tests."""
    os.environ["API_KEY"] = "test-key"


def _clear_test_api_key() -> None:
    """Limpia API_KEY después de tests."""
    os.environ.pop("API_KEY", "")


def create_test_client() -> AsyncClient:
    """Crea un AsyncClient de test con repos dobles."""
    _set_test_api_key()
    app = create_app()
    # Override repos con dobles frescos
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def create_test_client_sync() -> object:
    """Crea un TestClient síncrono para tests simples."""
    from fastapi.testclient import TestClient

    _set_test_api_key()
    app = create_app()
    app.state.repo = RepositorioAnalisisDoble()
    app.state.cache_vt = CacheVTDoble()
    return TestClient(app)
