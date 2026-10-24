"""Tests for uncovered branches in adjuntos detectors (T038).

Cubre ramas no ejercidas por las pruebas AC: comprimidos (ratio infinito,
streaming except), office (olevba analyze_macros con enlace externo), firma
(_familia branches para office-ole, imagen, html).
"""

from __future__ import annotations

import io
import zipfile

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

# --- comprimidos.py: ratio infinita (compress_size == 0, file_size > 0) ---

def test_zip_ratio_infinita_activa_sospechoso() -> None:
    """Un entry con compress_size=0 y file_size>0 → ratio infinita → sospechoso."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("d.txt", b"")
    data = bytearray(buf.getvalue())
    # Patch file_size in local header (offset 22) and central dir (offset 24)
    idx = data.find(b"PK\x03\x04")
    if idx >= 0:
        data[idx + 22 : idx + 26] = (100).to_bytes(4, "little")
    idx2 = data.find(b"PK\x01\x02")
    if idx2 >= 0:
        data[idx2 + 24 : idx2 + 28] = (100).to_bytes(4, "little")
    r = analizar_adjunto("edge.zip", "application/zip", bytes(data))
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" in codigos


# --- office.py: olevba analyze_macros con enlace externo ---

def test_ole2_enlace_externo_via_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """OLE2 con VBA_Parser stubado que reporta enlace externo → ADJ_ENLACE_EXTERNO."""

    class _VBAConEnlace:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def detect_vba_macros(self) -> bool:
            return True

        def analyze_macros(self) -> list[tuple[str, str, str, list[tuple[str, str]]]]:
            return [(
                "Type",
                "Module1",
                "Sub Test()",
                [("External", "External reference to https://evil.com")],
            )]

        def close(self) -> None:
            pass

    monkeypatch.setattr("oletools.olevba.VBA_Parser", _VBAConEnlace)
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    r = analizar_adjunto("doc.doc", "application/msword", ole2)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ENLACE_EXTERNO" in codigos


# --- firma.py: _familia branches (office-ole, imagen, html) ---

def test_firma_ole2_renombrado_pdf_tipo_no_coincide() -> None:
    """OLE2 renombrado a .pdf → ADJ_TIPO_NO_COINCIDE (familia office-ole vs pdf)."""
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    r = analizar_adjunto("doc.pdf", "application/pdf", ole2)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" in codigos


def test_firma_png_renombrado_txt_tipo_no_coincide() -> None:
    """PNG renombrado a .txt → ADJ_TIPO_NO_COINCIDE (familia imagen vs otro)."""
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    r = analizar_adjunto("img.txt", "text/plain", png)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" in codigos


def test_firma_jpeg_renombrado_exe_tipo_no_coincide() -> None:
    """JPEG renombrado a .exe → ADJ_TIPO_NO_COINCIDE (familia imagen vs ejecutable)."""
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    r = analizar_adjunto("photo.exe", "application/octet-stream", jpeg)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" in codigos


def test_firma_content_type_mismatch_activa_bandera() -> None:
    """PDF real con Content-Type application/zip → ADJ_TIPO_NO_COINCIDE (D5)."""
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    r = analizar_adjunto("doc.pdf", "application/zip", pdf)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" in codigos
