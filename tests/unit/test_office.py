"""Pruebas del detector de Office: macros y enlaces externos (FR-004).

OOXML (docx) con vbaProject.bin → ADJ_MACRO; con TargetMode="External" →
ADJ_ENLACE_EXTERNO. OLE2 con doble de olevba (sin librería real en CI).
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos import analizar_adjunto


def _docx_con_macro() -> bytes:
    """docx (zip) con word/vbaProject.bin → ADJ_MACRO."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("word/document.xml", b"<document/>")
        zf.writestr("word/vbaProject.bin", b"\x00" * 20)
    return buf.getvalue()


def _docx_con_enlace_externo() -> bytes:
    """docx con relación TargetMode="External" → ADJ_ENLACE_EXTERNO."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("word/document.xml", b"<document/>")
        zf.writestr(
            "word/_rels/document.xml.rels",
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="r1" Type="http://evil" Target="https://evil.com"'
            b' TargetMode="External"/>'
            b"</Relationships>",
        )
    return buf.getvalue()


def _docx_benigno() -> bytes:
    """docx sin macros ni enlaces externos."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("word/document.xml", b"<document/>")
    return buf.getvalue()


_MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_docx_con_macro_activa_adj_macro() -> None:
    r = analizar_adjunto("doc.docx", _MIME_DOCX, _docx_con_macro())
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_MACRO" in codigos


def test_docx_con_enlace_externo_activa_adj_enlace() -> None:
    r = analizar_adjunto("doc.docx", _MIME_DOCX, _docx_con_enlace_externo())
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ENLACE_EXTERNO" in codigos


def test_docx_benigno_sin_banderas_office() -> None:
    r = analizar_adjunto("doc.docx", _MIME_DOCX, _docx_benigno())
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_MACRO" not in codigos
    assert "ADJ_ENLACE_EXTERNO" not in codigos


def test_ole2_con_doble_de_olevba(monkeypatch: pytest.MonkeyPatch) -> None:
    """OLE2 con VBA_Parser stubado: macro encontrada → ADJ_MACRO (sin olevba real)."""

    class _VBAFalso:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def detect_vba_macros(self) -> bool:
            return True

        def analyze_macros(self) -> list[tuple[str, str, str, list[tuple[str, str]]]]:
            return [("Type", "Module1", "Sub Test()", [("AutoOpen", "Auto-open macro")])]

        def close(self) -> None:
            pass


    monkeypatch.setattr("oletools.olevba.VBA_Parser", _VBAFalso)
    # OLE2 magic + extensión .doc
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    r = analizar_adjunto("doc.doc", "application/msword", ole2)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_MACRO" in codigos


def test_ole2_olevba_falla_degrada_a_sospechoso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si olevba falla, el OLE2 degrada a ADJ_ARCHIVO_SOSPECHOSO (V.1)."""

    class _VBARoto:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("OLE2 inválido")

    monkeypatch.setattr("oletools.olevba.VBA_Parser", _VBARoto)
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    r = analizar_adjunto("doc.doc", "application/msword", ole2)
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" in codigos
