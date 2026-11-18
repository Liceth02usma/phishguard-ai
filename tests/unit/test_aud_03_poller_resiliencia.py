"""Auditoría AUD-03 (integración): resiliencia de `process_message`.

Verifica que el ciclo del poller sobreviva a fallos de cada etapa
(análisis, acciones, persistencia) sin tumbar el loop de monitoreo
(spec 013: resiliencia del poller — observada como NO implementada en
`gmail_poller.py`: sin reintentos de persistencia, solo try/except).

También documenta el defecto AUD-02 en el flujo completo:
`EntradaAcciones.remitente` llega vacío porque `headers` no es JSON.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest


class _FakeRequest:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def execute(self) -> dict[str, Any]:
        return self._data


class _FakeMessages:
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


def _service_con_eml(fabrica_eml: Callable[..., bytes]) -> _FakeService:
    eml = fabrica_eml(
        texto="cuerpo",
        html="<html><body>cuerpo</body></html>",
        remitente="juan.perez@empresa.com",
    )
    raw_b64 = base64.urlsafe_b64encode(eml).decode("ASCII")
    return _FakeService({"raw": raw_b64})


def _reporte(**kw: Any) -> Any:
    from src.level2_agent.models import PhishingReport

    base: dict[str, Any] = dict(
        resumen="resumen",
        analisis_tecnico="analisis",
        indicadores_phishing=[],
        es_phishing=False,
        nivel_severidad="Bajo",
        justificacion_veredicto="justificacion",
        veredicto="sin_indicadores",
        score_clasificador=10.0,
        version_modelo="v1",
    )
    base.update(kw)
    return PhishingReport(**base)


def test_analyze_falla_no_tumba_ciclo(
    fabrica_eml: Callable[..., bytes],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Si analyze_email lanza, process_message registra el error y NO propaga."""
    import src.gmail_integration.gmail_poller as mod_poller

    service = _service_con_eml(fabrica_eml)

    def _falla(email_data: Any) -> Any:
        raise RuntimeError("LLM caído (doble de auditoría)")

    monkeypatch.setattr(mod_poller, "analyze_email", _falla)

    # No debe lanzar: el loop de polling continúa con el siguiente correo.
    mod_poller.process_message(service, "msg-aud-fail")

    assert "Error procesando mensaje" in caplog.text


def test_acciones_fallan_hace_fallback_etiquetado(
    fabrica_eml: Callable[..., bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si ejecutar_acciones lanza, el fallback etiqueta el correo malicioso."""
    import src.gmail_integration.gmail_poller as mod_poller
    import src.gmail_integration.gmail_reader as mod_reader
    import src.level2_agent.acciones as mod_acciones
    import src.level2_agent.persistencia as mod_persistencia

    service = _service_con_eml(fabrica_eml)
    reporte = _reporte(es_phishing=True, veredicto="malicioso", nivel_severidad="Alto")
    monkeypatch.setattr(mod_poller, "analyze_email", lambda ed: reporte)

    def _falla(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Jira caído (doble de auditoría)")

    monkeypatch.setattr(mod_acciones, "ejecutar_acciones", _falla)

    etiquetados: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        mod_reader, "move_to_label", lambda *a, **k: etiquetados.append(a)
    )
    # Aísalo de la BD real de persistencia.
    monkeypatch.setattr(mod_persistencia, "guardar_analisis", lambda *a, **k: "x")

    mod_poller.process_message(service, "msg-aud-fallback")

    assert etiquetados, "el fallback move_to_label no se ejecutó"
    assert etiquetados[0][1] == "msg-aud-fallback"
    assert etiquetados[0][2] == "Phishing Alertas"


def test_persistencia_falla_no_tumba_ciclo(
    fabrica_eml: Callable[..., bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si guardar_analisis lanza (Mongo caído), el ciclo NO se interrumpe."""
    import src.gmail_integration.gmail_poller as mod_poller
    import src.level2_agent.acciones as mod_acciones
    import src.level2_agent.persistencia as mod_persistencia

    service = _service_con_eml(fabrica_eml)
    reporte = _reporte()
    monkeypatch.setattr(mod_poller, "analyze_email", lambda ed: reporte)

    # Acciones resueltas sin efectos (doble).
    monkeypatch.setattr(
        mod_acciones,
        "ejecutar_acciones",
        lambda *a, **k: SimpleNamespace(acciones=[], ticket_key=None),
    )

    llamadas = {"n": 0}

    def _falla(*args: Any, **kwargs: Any) -> Any:
        llamadas["n"] += 1
        raise RuntimeError("Mongo sin primary (doble de auditoría)")

    monkeypatch.setattr(mod_persistencia, "guardar_analisis", _falla)

    # No debe lanzar: la pérdida de persistencia solo se registra (AUD-A02:
    # sin reintento — caracterización del comportamiento actual).
    mod_poller.process_message(service, "msg-aud-persist")

    assert llamadas["n"] == 1, "guardar_analisis debió intentarse una vez"


def test_remitente_flujo_completo(
    fabrica_eml: Callable[..., bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flujo completo: el remitente del .eml debe llegar a EntradaAcciones."""
    import src.gmail_integration.gmail_poller as mod_poller
    import src.level2_agent.acciones as mod_acciones
    import src.level2_agent.persistencia as mod_persistencia

    service = _service_con_eml(fabrica_eml)
    reporte = _reporte(veredicto="revision_manual")
    monkeypatch.setattr(mod_poller, "analyze_email", lambda ed: reporte)

    capturas: dict[str, Any] = {}

    def _captura(entrada: Any, **kwargs: Any) -> Any:
        capturas["entrada"] = entrada
        return SimpleNamespace(acciones=[], ticket_key=None)

    monkeypatch.setattr(mod_acciones, "ejecutar_acciones", _captura)
    monkeypatch.setattr(mod_persistencia, "guardar_analisis", lambda *a, **k: "x")

    mod_poller.process_message(service, "msg-aud-remitente")

    assert "entrada" in capturas, "ejecutar_acciones no fue invocado"
    assert capturas["entrada"].remitente == "juan.perez@empresa.com"
