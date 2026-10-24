"""AC-ADJ-03: doble extensión y tipo no coincidente.

`factura.pdf.exe` → ADJ_DOBLE_EXTENSION; un `.exe` renombrado a `.pdf` →
ADJ_TIPO_NO_COINCIDE.
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

_PE_BYTES = b"MZ" + b"\x00" * 100 + b"PE\x00\x00" + b"\x00" * 50


@pytest.mark.ac("AC-ADJ-03")
def test_doble_extension_factura_pdf_exe() -> None:
    """factura.pdf.exe activa ADJ_DOBLE_EXTENSION y ADJ_EXTENSION_RIESGO."""
    r = analizar_adjunto("factura.pdf.exe", "application/octet-stream", _PE_BYTES)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_DOBLE_EXTENSION" in codigos
    assert "ADJ_EXTENSION_RIESGO" in codigos


@pytest.mark.ac("AC-ADJ-03")
def test_exe_renombrado_pdf_activa_tipo_no_coincide() -> None:
    """Un .exe renombrado a .pdf activa ADJ_TIPO_NO_COINCIDE."""
    r = analizar_adjunto("factura.pdf", "application/pdf", _PE_BYTES)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" in codigos


@pytest.mark.ac("AC-ADJ-03")
def test_benign_pdf_no_tipo_no_coincide() -> None:
    """Un PDF real con extensión .pdf NO activa ADJ_TIPO_NO_COINCIDE."""
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    r = analizar_adjunto("doc.pdf", "application/pdf", pdf)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_TIPO_NO_COINCIDE" not in codigos
