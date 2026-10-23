"""Pruebas del Adapter RDAP: caché, TTL y boundary de dominio nuevo (research D7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.motor import evaluar_banderas
from src.level2_agent.banderas.rdap import CacheRDAP, crear_consultor_rdap

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
    assert consultor("x.com") == cliente.fecha
    assert consultor("x.com") == cliente.fecha
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
    assert consultor("x.com") is None
    assert consultor("x.com") is None  # memoizado en la misma invocacion
    assert cliente.llamadas == 1


def test_dominio_nuevo_valores_limite(construir_correo: Any, rdap_fijo: Any) -> None:
    """29 dias -> nuevo; 30 y 31 dias -> no nuevo (boundary de 30, catalogo 5.1)."""
    config = ConfigBanderas(authserv_id="mio.com")
    for dias, esperado in ((29, True), (30, False), (31, False)):
        cliente = rdap_fijo(AHORA - timedelta(days=dias))
        correo = construir_correo(cabeceras=[("From", "ana@dominio.com")])
        r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=cliente)
        assert any(b.codigo == "DOMINIO_NUEVO" for b in r.banderas) is esperado
