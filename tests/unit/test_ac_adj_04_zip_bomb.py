"""AC-ADJ-04: zip bomb (relación > 100:1) aborta sin agotar memoria.

Valores límite: 99:1 y 100:1 → sin bandera; 101:1 → aborto +
ADJ_ARCHIVO_SOSPECHOSO. Se usa una config con ratio_maximo reducido para
ejercer el borde exacto de forma determinista (research D8).
"""

from __future__ import annotations

import io
import math
import zipfile

import pytest
from src.level2_agent.adjuntos import ConfigAdjuntos, analizar_adjunto


def _zip_de_ceros(n_bytes: int) -> bytes:
    """Crea un zip con un solo entry de n_bytes de ceros (alta compresión)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", b"\x00" * n_bytes)
    return buf.getvalue()


def _zip_de_aleatorio(n_bytes: int) -> bytes:
    """Crea un zip con datos incompresibles (semilla fija, sin azar — Art. II.5)."""
    import random

    rng = random.Random(42)
    datos = bytes(rng.getrandbits(8) for _ in range(n_bytes))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.bin", datos)
    return buf.getvalue()


def _ratio_real(zip_bytes: bytes) -> float:
    """Mide la relación real de un zip (descomprimido / comprimido)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        info = zf.infolist()[0]
        return info.file_size / info.compress_size if info.compress_size else float("inf")


@pytest.mark.ac("AC-ADJ-04")
def test_zip_bomb_alta_relacion_aborta() -> None:
    """Un zip con relación >> 100:1 aborta con ADJ_ARCHIVO_SOSPECHOSO."""
    bomb = _zip_de_ceros(100_000)  # ratio muy alto
    assert _ratio_real(bomb) > 100
    r = analizar_adjunto("bomb.zip", "application/zip", bomb)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" in codigos


@pytest.mark.ac("AC-ADJ-04")
def test_zip_normal_no_aborta() -> None:
    """Un zip con relación baja (~1:1) NO activa ADJ_ARCHIVO_SOSPECHOSO."""
    normal = _zip_de_aleatorio(1000)
    assert _ratio_real(normal) < 100
    r = analizar_adjunto("normal.zip", "application/zip", normal)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in codigos


@pytest.mark.ac("AC-ADJ-04")
def test_borde_ratio_exacto_no_bandera() -> None:
    """En el límite exacto (ratio == ratio_maximo) NO hay bandera (spec 002 convention)."""
    zip_data = _zip_de_ceros(10_000)
    ratio = math.ceil(_ratio_real(zip_data))
    # Config con ratio_maximo justo en la relación real → sin bandera
    config = ConfigAdjuntos.defecto()
    config = config.model_copy(update={"ratio_maximo_zip": ratio})
    r = analizar_adjunto("edge.zip", "application/zip", zip_data, config=config)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in codigos


@pytest.mark.ac("AC-ADJ-04")
def test_borde_ratio_uno_mas_si_bandera() -> None:
    """Con ratio_maximo = ratio_real - 1 (uno menos) → hay bandera (>)."""
    zip_data = _zip_de_ceros(10_000)
    ratio = math.ceil(_ratio_real(zip_data))
    config = ConfigAdjuntos.defecto()
    config = config.model_copy(update={"ratio_maximo_zip": ratio - 1})
    r = analizar_adjunto("over.zip", "application/zip", zip_data, config=config)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" in codigos
