"""AC-ADJ-02: EICAR se identifica por hash y queda disponible para la spec 06.

El EICAR se genera en memoria (SC-003): nunca se escribe a disco. El hash
de referencia es una constante publicada (research D9).
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

from vector_eicar import EICAR_SHA256, generar_eicar


@pytest.mark.ac("AC-ADJ-02")
def test_eicar_identificado_por_hash() -> None:
    """El SHA-256 del EICAR coincide con la referencia publicada."""
    eicar = generar_eicar()
    r = analizar_adjunto("eicar.com", "application/octet-stream", eicar)
    assert r.sha256 == EICAR_SHA256


@pytest.mark.ac("AC-ADJ-02")
def test_eicar_extension_riesgo() -> None:
    """EICAR con extensión .com activa ADJ_EXTENSION_RIESGO."""
    r = analizar_adjunto("eicar.com", "application/octet-stream", generar_eicar())
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_EXTENSION_RIESGO" in codigos


@pytest.mark.ac("AC-ADJ-02")
def test_eicar_helper_importable() -> None:
    """El helper EICAR es importable por la spec 006 (research D9)."""
    eicar = generar_eicar()
    assert isinstance(eicar, bytes)
    assert len(eicar) == 68  # cadena EICAR estándar: 68 bytes
    assert EICAR_SHA256 == "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
