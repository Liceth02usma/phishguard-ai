"""Configuración desde variables de entorno (research D9 + clarify FR-002)."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, ConfiguracionError


@pytest.mark.ac("AC-VT-02")
def test_premium_sin_rpm_daily_usa_defaults_public() -> None:
    """Clarify FR-002: premium sin VT_RPM/VT_DAILY → 4/min y 500/día (defaults públicos)."""
    config = ConfigVT.desde_entorno({"VT_TIER": "premium"})
    assert config.tier == "premium"
    assert config.rpm == 4
    assert config.tope_dia == 500


@pytest.mark.ac("AC-VT-02")
def test_premium_con_limites_explicitos_los_respeta() -> None:
    """Clarify FR-002: premium solo eleva cuando se configura explícitamente."""
    config = ConfigVT.desde_entorno(
        {"VT_TIER": "premium", "VT_RPM": "30", "VT_DAILY": "10000"}
    )
    assert config.rpm == 30
    assert config.tope_dia == 10000


@pytest.mark.ac("AC-VT-02")
def test_public_con_defaults() -> None:
    """VT_TIER vacío o public conserva 4/500 y flags apagados."""
    assert ConfigVT.desde_entorno({}).tier == "public"
    config = ConfigVT.desde_entorno({"VT_TIER": "public"})
    assert (config.rpm, config.tope_dia) == (4, 500)
    assert config.upload_unknown is False
    assert config.submit_unknown_urls is False
    assert config.max_por_correo == 10


@pytest.mark.ac("AC-VT-02")
@pytest.mark.parametrize("tier", ["free", "business", "Public ", "PREMIUM"])
def test_tier_inválido_lanza_configuracion_error(tier: str) -> None:
    """VT_TIER fuera de {public, premium} → ConfiguracionError antes de consultar (III.9)."""
    with pytest.raises(ConfiguracionError):
        ConfigVT.desde_entorno({"VT_TIER": tier})


@pytest.mark.ac("AC-VT-02")
@pytest.mark.parametrize(
    ("variable", "valor"),
    [
        ("VT_MAX_POR_CORREO", "cero"),
        ("VT_MAX_POR_CORREO", "0"),
        ("VT_RPM", "0"),
        ("VT_RPM", "-1"),
        ("VT_DAILY", "-5"),
        ("VT_UMBRAL_MALICIOSA", "0"),
    ],
)
def test_enteros_inválidos_lanzan_configuracion_error(variable: str, valor: str) -> None:
    """Valor no numérico o fuera de rango → ConfiguracionError antes de consultar (III.9)."""
    with pytest.raises(ConfiguracionError):
        ConfigVT.desde_entorno({variable: valor})


@pytest.mark.ac("AC-VT-02")
@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("true", True), ("True", True), ("1", True), ("YES", True), ("false", False), ("0", False), ("", False)],
)
def test_booleanos_true_1_yes_case_insensitive(valor: str, esperado: bool) -> None:
    """'true'/'1'/'yes' en cualquier mayúscula → True; cualquier otra cosa → False (D9)."""
    config = ConfigVT.desde_entorno(
        {"VT_UPLOAD_UNKNOWN": valor, "VT_SUBMIT_UNKNOWN_URLS": valor}
    )
    assert config.upload_unknown is esperado
    assert config.submit_unknown_urls is esperado


@pytest.mark.ac("AC-VT-07")
def test_api_key_no_serializa_ni_repr() -> None:
    """La clave no aparece en repr ni en la serialización (FR-009, AC-VT-07)."""
    config = ConfigVT.desde_entorno({"VT_API_KEY": "secreta-12345"})
    assert config.api_key == "secreta-12345"
    assert "secreta-12345" not in repr(config)
    assert "secreta-12345" not in str(config.model_dump())
    assert "api_key" not in config.model_dump()
