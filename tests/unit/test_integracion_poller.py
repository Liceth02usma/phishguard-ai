"""Integración del poller: `process_message` produce un `EmailData` normalizado."""

from __future__ import annotations

import base64
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest


class _FakeRequest:
    """Doble de la petición de Gmail: `execute()` devuelve los datos fijos."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def execute(self) -> dict[str, Any]:
        return self._data


class _FakeMessages:
    """Doble de `users().messages()`; `get(...).execute()` devuelve el correo crudo."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, **kwargs: Any) -> _FakeRequest:
        return _FakeRequest(self._data)

    def modify(self, **kwargs: Any) -> _FakeRequest:
        return _FakeRequest({})


class _FakeUsers:
    def __init__(self, data: dict[str, Any]) -> None:
        self._msgs = _FakeMessages(data)

    def messages(self) -> _FakeMessages:
        return self._msgs


class _FakeService:
    def __init__(self, data: dict[str, Any]) -> None:
        self._users = _FakeUsers(data)

    def users(self) -> _FakeUsers:
        return self._users


@pytest.mark.ac("AC-NORM-01")
def test_poller_construye_emaildata_normalizado(
    fabrica_eml: Callable[..., bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`process_message` pasa a `analyze_email` un `EmailData` con origen y cabeceras."""
    import src.gmail_integration.gmail_poller as mod_poller

    eml = fabrica_eml(texto="hola", remitente="juan.perez@empresa.com")
    raw_b64 = base64.urlsafe_b64encode(eml).decode("ASCII")
    service = _FakeService({"raw": raw_b64})

    capturas: dict[str, Any] = {}
    reporte = SimpleNamespace(es_phishing=False, nivel_severidad="Bajo", indicadores_phishing=[])

    def _capturar(ed: Any) -> Any:
        capturas["email"] = ed
        return reporte

    monkeypatch.setattr(mod_poller, "analyze_email", _capturar)
    monkeypatch.setattr(mod_poller, "move_to_label", lambda *a, **k: None)
    monkeypatch.setattr(mod_poller, "mark_as_read", lambda *a, **k: None)

    mod_poller.process_message(service, "msgid-123")

    ed = capturas["email"]
    assert ed.message_id == "msgid-123"
    assert ed.origen == "gmail"
    assert any(c.nombre.lower() == "received" for c in ed.cabeceras)
    assert "hola" in ed.texto_limpio
