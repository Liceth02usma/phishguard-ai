"""Pruebas del Adapter RDAP: caché, TTL y boundary de dominio nuevo (research D7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.modelos import TIMEOUT_RDAP_SEGUNDOS, EdadDominio
from src.level2_agent.banderas.motor import evaluar_banderas
from src.level2_agent.banderas.rdap import (
    CacheRDAP,
    RequestsRDAP,
    cache_proceso,
    crear_consultor_rdap,
    reiniciar_cache_proceso,
)

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class _Contador:
    """Cliente RDAP de prueba que cuenta llamadas y devuelve una fecha fija."""

    def __init__(self, fecha: Any) -> None:
        self.fecha = fecha
        self.llamadas = 0

    def registrar_evento(self, dominio: str) -> Any:
        self.llamadas += 1
        return self.fecha


def test_cache_hit_no_repide_consulta() -> None:
    cliente = _Contador(AHORA - timedelta(days=10))
    consultor = crear_consultor_rdap(cliente, CacheRDAP(), AHORA)
    assert consultor("x.com").fecha_registro == cliente.fecha
    assert consultor("x.com").fecha_registro == cliente.fecha
    assert cliente.llamadas == 1  # cacheado (TTL 7 dias)


def test_cache_expira_tras_ttl() -> None:
    cliente = _Contador(AHORA - timedelta(days=10))
    cache = CacheRDAP()
    crear_consultor_rdap(cliente, cache, AHORA)("x.com")
    # 8 dias despues el TTL (7 dias) vencio -> vuelve a consultar
    crear_consultor_rdap(cliente, cache, AHORA + timedelta(days=8))("x.com")
    assert cliente.llamadas == 2


def test_falla_no_lanza_y_no_cachea() -> None:
    cliente = _Contador(None)  # RDAP caido
    consultor = crear_consultor_rdap(cliente, CacheRDAP(), AHORA)
    assert consultor("x.com").fecha_registro is None
    assert consultor("x.com").fecha_registro is None  # memoizado en la misma invocacion
    assert cliente.llamadas == 1


def test_cache_ttl_valores_limite() -> None:
    """D10.1: a 6d23h hay golpe de cache; a los 7 dias exactos expira y reconsulta."""
    cliente = _Contador(AHORA - timedelta(days=400))
    cache = CacheRDAP()
    crear_consultor_rdap(cliente, cache, AHORA)("x.com")
    golpe = crear_consultor_rdap(cliente, cache, AHORA + timedelta(hours=167))
    assert golpe("x.com").fecha_registro == cliente.fecha
    assert cliente.llamadas == 1  # 6d23h < TTL 7d -> hit
    reconsulta = crear_consultor_rdap(cliente, cache, AHORA + timedelta(days=7))
    reconsulta("x.com")
    assert cliente.llamadas == 2  # 7d exactos -> expira (ahora >= expira)


def test_dominio_malformado_no_compone_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """D7/V.5: dominio con ruta, esquema, query o espacios nunca llega a requests."""
    llamadas: list[str] = []

    def _get(url: str, **kwargs: Any) -> Any:
        llamadas.append(url)
        raise AssertionError("no debe consultarse con un dominio malformado")

    monkeypatch.setattr("src.level2_agent.banderas.rdap.requests.get", _get)
    cliente = RequestsRDAP()
    malformados = ("evil.com/../ruta", "https://x.com", "dominio con espacio", "x.com?q=1", "")
    for dominio in malformados:
        assert cliente.registrar_evento(dominio) is None  # sin excepcion (AC-HDR-06)
    assert llamadas == []  # ninguna URL compuesta con dominio malformado


def test_consultor_devuelve_edad_dominio() -> None:
    """El consultor envuelve la fecha en EdadDominio (data-model: EdadDominio)."""
    cliente = _Contador(AHORA - timedelta(days=10))
    resultado = crear_consultor_rdap(cliente, CacheRDAP(), AHORA)("x.com")
    assert isinstance(resultado, EdadDominio)
    assert resultado.fecha_registro == cliente.fecha


def test_dominio_nuevo_valores_limite(construir_correo: Any, rdap_fijo: Any) -> None:
    """29 dias -> nuevo; 30 y 31 dias -> no nuevo (boundary de 30, catalogo 5.1)."""
    config = ConfigBanderas(authserv_id="mio.com")
    for dias, esperado in ((29, True), (30, False), (31, False)):
        reiniciar_cache_proceso()  # cada fecha se prueba con cache limpia
        cliente = rdap_fijo(AHORA - timedelta(days=dias))
        correo = construir_correo(cabeceras=[("From", "ana@dominio.com")])
        r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=cliente)
        assert any(b.codigo == "DOMINIO_NUEVO" for b in r.banderas) is esperado


def test_cache_de_proceso_persiste_entre_invocaciones(construir_correo: Any) -> None:
    """La cache de proceso evita repetir la consulta RDAP en correos sucesivos (plan: storage)."""
    config = ConfigBanderas(authserv_id="mio.com")
    cliente = _Contador(AHORA - timedelta(days=400))
    correo = construir_correo(cabeceras=[("From", "ana@dominio-a.com")])
    r1 = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=cliente)
    r2 = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=cliente)
    assert r1.puntos_totales == r2.puntos_totales
    assert cliente.llamadas == 1  # la 2a invocacion golpea la cache compartida


def test_cache_de_proceso_compartida_y_reinunciable() -> None:
    """Hay una unica cache de proceso y ``reiniciar_cache_proceso`` la vacia (Art. II.5)."""
    assert cache_proceso() is cache_proceso()
    cache_proceso().guardar("x.com", AHORA - timedelta(days=1), AHORA)
    reiniciar_cache_proceso()
    assert cache_proceso().obtener("x.com", AHORA) is None


class _RespuestaOk:
    """Respuesta RDAP simulada con evento de registro."""

    status_code = 200

    @staticmethod
    def json() -> dict[str, Any]:
        return {
            "events": [
                {"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}
            ]
        }


def test_requests_rdap_usa_timeout_en_cada_intento(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada intento RDAP respeta TIMEOUT_RDAP_SEGUNDOS (edge: RDAP lento >5 s)."""
    llamadas: list[dict[str, Any]] = []

    def _get(url: str, **kwargs: Any) -> Any:
        llamadas.append(kwargs)
        return _RespuestaOk()

    monkeypatch.setattr("src.level2_agent.banderas.rdap.requests.get", _get)
    cliente = RequestsRDAP()
    assert cliente.registrar_evento("ejemplo.com") is not None
    assert llamadas, "no se realizo ninguna consulta"
    assert all(kw.get("timeout") == TIMEOUT_RDAP_SEGUNDOS for kw in llamadas)
