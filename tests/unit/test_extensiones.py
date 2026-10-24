"""Tabla de decisión: extensión × firma × content-type → banderas (D4/D5).

Verifica las 12 filas de data-model.md a través de analizar_adjunto.
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

_PE = b"MZ" + b"\x00" * 100
_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _codigos(nombre: str, tipo: str, payload: bytes) -> set[str]:
    return {b.codigo for b in analizar_adjunto(nombre, tipo, payload).banderas}


@pytest.mark.ac("AC-ADJ-03")
def test_fila_1_pdf_benigno_sin_banderas() -> None:
    assert "ADJ_TIPO_NO_COINCIDE" not in _codigos("doc.pdf", "application/pdf", _PDF)


def test_fila_2_pdf_firma_exe_tipo_no_coincide() -> None:
    assert "ADJ_TIPO_NO_COINCIDE" in _codigos("doc.pdf", "application/pdf", _PE)


def test_fila_3_exe_riesgo() -> None:
    assert "ADJ_EXTENSION_RIESGO" in _codigos("evil.exe", "application/octet-stream", _PE)


def test_fila_4_pdf_exe_doble_y_riesgo() -> None:
    c = _codigos("factura.pdf.exe", "application/octet-stream", _PE)
    assert "ADJ_EXTENSION_RIESGO" in c
    assert "ADJ_DOBLE_EXTENSION" in c


def test_fila_5_espacio_antes_extension_doble() -> None:
    c = _codigos("factura .pdf", "application/pdf", _PDF)
    assert "ADJ_DOBLE_EXTENSION" in c


def test_fila_6_html_bandera_html() -> None:
    c = _codigos("page.html", "text/html", b"<html></html>")
    assert "ADJ_HTML" in c
    assert "ADJ_EXTENSION_RIESGO" not in c


def test_fila_7_svg_bandera_html() -> None:
    c = _codigos("img.svg", "image/svg+xml", b"<svg></svg>")
    assert "ADJ_HTML" in c


def test_fila_8_lnk_riesgo() -> None:
    c = _codigos("access.lnk", "application/octet-stream", b"\x00" * 50)
    assert "ADJ_EXTENSION_RIESGO" in c


def test_fila_9_txt_sin_banderas() -> None:
    c = _codigos("notas.txt", "text/plain", b"hola mundo")
    assert "ADJ_EXTENSION_RIESGO" not in c
    assert "ADJ_HTML" not in c


def test_fila_11_jpg_exe_doble_y_riesgo() -> None:
    c = _codigos("foto.jpg.exe", "application/octet-stream", _PE)
    assert "ADJ_EXTENSION_RIESGO" in c
    assert "ADJ_DOBLE_EXTENSION" in c


def test_fila_12_pdf_firma_zip_tipo_no_coincide() -> None:
    """Un zip renombrado a .pdf activa ADJ_TIPO_NO_COINCIDE."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", b"x")
    c = _codigos("doc.pdf", "application/zip", buf.getvalue())
    assert "ADJ_TIPO_NO_COINCIDE" in c
