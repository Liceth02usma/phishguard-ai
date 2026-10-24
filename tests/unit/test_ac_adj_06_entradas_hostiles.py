"""AC-ADJ-06: adjunto vacío, truncado o con nombre hostil no lanza excepción.

Propiedades con hypothesis: analizar_adjunto nunca lanza, es determinista y
produce hashes válidos para bytes y nombres arbitrarios (research D11/D14).
"""

from __future__ import annotations

import io
import zipfile

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.level2_agent.adjuntos import analizar_adjunto

from vector_eicar import generar_eicar


@pytest.mark.ac("AC-ADJ-06")
def test_payload_vacio_no_lanza() -> None:
    r = analizar_adjunto("vacio.txt", "text/plain", b"")
    assert r.tamano_bytes == 0
    assert len(r.sha256) == 64


@pytest.mark.ac("AC-ADJ-06")
def test_zip_truncado_no_lanza() -> None:
    """Un zip truncado no lanza excepción no controlada."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", b"hola")
    truncado = buf.getvalue()[:10]  # zip incompleto
    r = analizar_adjunto("trunc.zip", "application/zip", truncado)
    assert len(r.sha256) == 64  # el hash siempre se calcula


@pytest.mark.ac("AC-ADJ-06")
def test_nombre_con_puntos_puntos_no_lanza() -> None:
    r = analizar_adjunto("../../etc/passwd", "text/plain", b"root:x:0:0")
    assert len(r.sha256) == 64


@pytest.mark.ac("AC-ADJ-06")
def test_nombre_ruta_absoluta_windows_no_lanza() -> None:
    r = analizar_adjunto(r"C:\Windows\system32\evil.exe", "application/octet-stream", b"MZ")
    assert len(r.sha256) == 64


@pytest.mark.ac("AC-ADJ-06")
def test_nombre_con_nul_no_lanza() -> None:
    r = analizar_adjunto("evil\x00.txt", "text/plain", b"data")
    assert len(r.sha256) == 64


@pytest.mark.ac("AC-ADJ-06")
def test_nombre_rtl_override_no_lanza() -> None:
    r = analizar_adjunto("ev\u202eil.exe", "text/plain", b"data")
    assert len(r.sha256) == 64


@given(st.binary(max_size=500), st.text(max_size=80))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], derandomize=True)
def test_nunca_lanza_y_hashes_validos(payload: bytes, nombre: str) -> None:
    """Para bytes y nombres arbitrarios, analizar_adjunto nunca lanza."""
    r = analizar_adjunto(nombre, "application/octet-stream", payload)
    assert len(r.sha256) == 64
    assert len(r.md5) == 32
    assert len(r.sha1) == 40


@given(st.binary(max_size=500))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow], derandomize=True)
def test_determinista(payload: bytes) -> None:
    """Misma entrada → misma salida (sin hora, azar ni red)."""
    r1 = analizar_adjunto("test.bin", "application/octet-stream", payload)
    r2 = analizar_adjunto("test.bin", "application/octet-stream", payload)
    assert r1 == r2


@pytest.mark.ac("AC-ADJ-06")
def test_detalles_sin_nombres_completos() -> None:
    """Los detalles y BanderaAdjunto.detalle no contienen el nombre del adjunto (D13, V.4)."""
    casos = [
        ("factura.pdf.exe", "application/octet-stream", b"MZ" + b"\x00" * 100),
        ("doc.pdf", "application/pdf", b"%PDF-1.4\n%%EOF\n"),
        ("data.zip", "application/zip", b"PK\x03\x04" + b"\x00" * 50),
        ("secret.txt", "text/plain", b"datos"),
        ("eicar.com", "application/octet-stream", generar_eicar()),
    ]
    for nombre, tipo, payload in casos:
        r = analizar_adjunto(nombre, tipo, payload)
        for b in r.banderas:
            assert nombre not in b.detalle, f"detalle contiene el nombre: {b.detalle}"
        for d in r.detalles:
            assert nombre not in d, f"detalles contiene el nombre: {d}"
