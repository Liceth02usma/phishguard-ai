"""TTL por tipo, entradas de caché y presupuesto por correo (FR-005/FR-006, data-model)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from src.level2_agent.virustotal import ConfigVT, Presupuesto, presupuesto_nuevo
from src.level2_agent.virustotal.cache import clave_cache, ttl_para
from src.level2_agent.virustotal.modelos import EntradaCache, LastAnalysisStats

INSTANTE = "2026-01-01T12:00:00+00:00"


@pytest.mark.ac("AC-VT-06")
@pytest.mark.parametrize(
    ("tipo", "es_desconocido", "esperado_dias"),
    [
        ("archivo", False, 7),
        ("url", False, 1),
        ("dominio", False, 1),
        ("ip", False, 1),
        ("archivo", True, 0),  # desconocido → 1 hora = 0 días
        ("url", True, 0),
    ],
)
def test_ttl_por_tipo(tipo: str, es_desconocido: bool, esperado_dias: int) -> None:
    """TTL literal: archivo 7 d; URL/dominio/IP 24 h; desconocido 1 h (FR-005)."""
    ttl = ttl_para(tipo, es_desconocido=es_desconocido)
    assert ttl == timedelta(days=esperado_dias)


@pytest.mark.ac("AC-VT-06")
def test_ttl_desconocido_es_exactamente_una_hora() -> None:
    """El TTL del desconocido es 1 h exacta (no un día) (FR-005)."""
    assert ttl_para("archivo", es_desconocido=True) == timedelta(hours=1)
    assert ttl_para("url", es_desconocido=True) == timedelta(hours=1)


@pytest.mark.ac("AC-VT-06")
def test_clave_cache_formateada() -> None:
    """La clave tiene el formato '{tipo}:{identificador}' (data-model)."""
    assert clave_cache("archivo", "ab12") == "archivo:ab12"
    assert clave_cache("url", "aGVsbG8") == "url:aGVsbG8"


@pytest.mark.ac("AC-VT-06")
def test_entrada_cache_inmutable() -> None:
    """EntradaCache es un dataclass congelado: no se puede mutar (data-model)."""
    from datetime import datetime

    desde = datetime.fromisoformat(INSTANTE)
    entrada = EntradaCache(
        clave="archivo:ab12",
        clasificacion="limpia",
        stats=LastAnalysisStats(harmless=30),
        guardada_en=desde,
        expira_en=desde + timedelta(days=7),
    )
    with pytest.raises(AttributeError):
        entrada.clasificacion = "maliciosa"  # type: ignore[misc]


@pytest.mark.ac("AC-VT-08")
def test_presupuesto_nuevo_toma_el_tope_de_config() -> None:
    """presupuesto_nuevo lee VT_MAX_POR_CORREO (default 10) (FR-006)."""
    assert presupuesto_nuevo(ConfigVT()).restantes == 10
    assert presupuesto_nuevo(ConfigVT(max_por_correo=3)).restantes == 3


@pytest.mark.ac("AC-VT-08")
def test_presupuesto_deshasta_hasta_agotarse() -> None:
    """usar() devuelve True exactamente N veces y luego False (FR-006, límite)."""
    presupuesto: Presupuesto = presupuesto_nuevo(ConfigVT(max_por_correo=2))
    assert presupuesto.usar() is True
    assert presupuesto.agotado is False
    assert presupuesto.usar() is True
    assert presupuesto.agotado is True
    assert presupuesto.usar() is False
    assert presupuesto.usar() is False  # estable tras agotarse


@pytest.mark.ac("AC-VT-08")
def test_presupuestos_independientes() -> None:
    """Cada presupuesto de correo es independiente de los demás (FR-006)."""
    uno = presupuesto_nuevo(ConfigVT(max_por_correo=1))
    dos = presupuesto_nuevo(ConfigVT(max_por_correo=1))
    assert uno.usar() is True
    assert dos.usar() is True
    assert uno.usar() is False
