"""AC-NORM-05: `juan.perez@empresa.com` se convierte en `j***@empresa.com`."""

from __future__ import annotations

import pytest
from src.level2_agent.normalizacion import enmascarar_texto


@pytest.mark.ac("AC-NORM-05")
def test_formato_basico() -> None:
    """Conserva primera letra del local y el dominio completo."""
    assert enmascarar_texto("juan.perez@empresa.com") == "j***@empresa.com"


@pytest.mark.ac("AC-NORM-05")
def test_local_part_de_una_letra() -> None:
    """Un local de una sola letra también se enmascara."""
    assert enmascarar_texto("a@b.com") == "a***@b.com"


@pytest.mark.ac("AC-NORM-05")
def test_varios_correos_en_texto() -> None:
    """Cada correo del texto se enmascara de forma independiente."""
    salida = enmascarar_texto("de ana.garcia@dominio.org a luis.rodriguez@corp.net")
    assert "a***@dominio.org" in salida
    assert "l***@corp.net" in salida
    assert "ana.garcia@dominio.org" not in salida
    assert "luis.rodriguez@corp.net" not in salida


@pytest.mark.ac("AC-NORM-05")
def test_dominio_con_subdominio_y_plus() -> None:
    """Se conserva el dominio con subdominio y el local con `+`/`%`."""
    salida = enmascarar_texto("pedro.gomez+spam@sub.empresa.com.co")
    assert salida == "p***@sub.empresa.com.co"


@pytest.mark.ac("AC-NORM-05")
def test_texto_sin_correos_inalterado() -> None:
    """El texto sin PII no se modifica."""
    assert enmascarar_texto("sin datos personales aqui") == "sin datos personales aqui"
