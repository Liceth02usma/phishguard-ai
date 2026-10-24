"""Pruebas del detector de PDF: /OpenAction, /JavaScript, /Launch (FR-004).

PDF con acciones peligrosas → ADJ_PDF_ACTIVO. PDF truncado →
ADJ_ARCHIVO_SOSPECHOSO. PDF benigno → sin banderas.
"""

from __future__ import annotations

import io

from src.level2_agent.adjuntos import analizar_adjunto


def _pdf(catalog_extra: str = "") -> bytes:
    """Construye un PDF mínimo con extras en el catálogo /Root."""
    obj1 = f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R {catalog_extra} >>\nendobj\n"
    obj2 = "2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    header = b"%PDF-1.4\n"
    body = (obj1 + obj2).encode("latin-1")
    xref_offset = len(header) + len(body)
    xref = (
        f"xref\n0 3\n"
        f"0000000000 65535 f \n"
        f"{len(header):010d} 00000 n \n"
        f"{len(header) + len(obj1.encode('latin-1')):010d} 00000 n \n"
        f"trailer\n<< /Root 1 0 R /Size 3 >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return header + body + xref


def _pdf_benigno() -> bytes:
    """PDF válido creado con pypdf (parseable, sin acciones)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _codigos(nombre: str, payload: bytes) -> set[str]:
    return {b.codigo for b in analizar_adjunto(nombre, "application/pdf", payload).banderas}


def test_pdf_con_open_action_activa_bandera() -> None:
    c = _codigos("doc.pdf", _pdf("/OpenAction << /S /GoTo >>"))
    assert "ADJ_PDF_ACTIVO" in c


def test_pdf_con_javascript_activa_bandera() -> None:
    c = _codigos("doc.pdf", _pdf("/Names << /JavaScript << >> >>"))
    assert "ADJ_PDF_ACTIVO" in c


def test_pdf_con_launch_activa_bandera() -> None:
    c = _codigos("doc.pdf", _pdf("/OpenAction << /S /Launch /F (x) >>"))
    assert "ADJ_PDF_ACTIVO" in c


def test_pdf_truncado_activa_sospechoso() -> None:
    pdf = _pdf()
    truncado = pdf[: len(pdf) // 2]
    c = _codigos("doc.pdf", truncado)
    assert "ADJ_ARCHIVO_SOSPECHOSO" in c


def test_pdf_vacio_activa_sospechoso() -> None:
    c = _codigos("doc.pdf", b"")
    assert "ADJ_ARCHIVO_SOSPECHOSO" in c


def test_pdf_benigno_sin_banderas_pdf() -> None:
    c = _codigos("doc.pdf", _pdf_benigno())
    assert "ADJ_PDF_ACTIVO" not in c
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in c
