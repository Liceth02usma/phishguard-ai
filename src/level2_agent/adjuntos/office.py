"""Detección de macros y enlaces externos en Office (FR-004).

OOXML (docx/xlsx/pptx): escaneo de `vbaProject.bin` y relaciones `TargetMode="External"`.
OLE2 (doc/xls/ppt): adapter `oletools.olevba` (research D6). Todo en memoria.
"""

from __future__ import annotations

import io
import zipfile
from typing import Protocol

from src.level2_agent.adjuntos.modelos import (
    BanderaAdjunto,
    ContextoAdjunto,
    ResultadoDetector,
    bandera,
)

_EXT_OOXML = frozenset({"docx", "xlsx", "pptx"})
_EXT_OLE2 = frozenset({"doc", "xls", "ppt"})
_MAGIA_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_MAGIA_ZIP = b"PK"


class AnalizadorOffice(Protocol):
    """Interfaz del analizador OLE2 (Adapter, research D6)."""

    def analizar(self, payload: bytes) -> tuple[bool, bool, str]:
        """Devuelve (tiene_macro, tiene_enlace_externo, detalle). Nunca lanza."""
        ...


class OlevbaOffice:
    """Implementación real con `oletools.olevba` (OLE2 macros/enlaces, D6)."""

    def analizar(self, payload: bytes) -> tuple[bool, bool, str]:
        """Analiza un OLE2 en memoria; degrada a detalle ante cualquier fallo."""
        try:
            from oletools.olevba import VBA_Parser

            vba = VBA_Parser(io.BytesIO(payload))
            macros = bool(vba.detect_vba_macros())
            enlaces = False
            if macros:
                for _tipo, _nombre, _codigo, analisis in vba.analyze_macros():
                    for palabra, descripcion in analisis:
                        texto = f"{palabra} {descripcion}".lower()
                        if "external" in texto or "link" in texto:
                            enlaces = True
                            break
                    if enlaces:
                        break
            vba.close()
            return (macros, enlaces, "")
        except Exception as exc:  # noqa: BLE001 — degrada, nunca propaga (D14)
            return (False, False, f"olevba fallo: {type(exc).__name__}")


_analizador_defecto = OlevbaOffice()


class OfficeDetector:
    """Detector de macros y enlaces externos en Office (FR-004)."""

    def __init__(self, analizador: AnalizadorOffice | None = None) -> None:
        self._analizador = analizador or _analizador_defecto

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        ext = ctx.extension_final.lower().lstrip(".")
        payload = ctx.payload
        es_ooxml = payload.startswith(_MAGIA_ZIP) and ext in _EXT_OOXML
        es_ole2 = payload.startswith(_MAGIA_OLE2) or ext in _EXT_OLE2

        if not es_ooxml and not es_ole2:
            return ResultadoDetector((), ())

        banderas: list[BanderaAdjunto] = []
        detalles: list[str] = []

        if es_ooxml:
            self._analizar_ooxml(payload, banderas, detalles)
        if es_ole2:
            self._analizar_ole2(payload, banderas, detalles)

        return ResultadoDetector(tuple(banderas), tuple(detalles))

    def _analizar_ooxml(
        self, payload: bytes, banderas: list[BanderaAdjunto], detalles: list[str]
    ) -> None:
        """Escanea OOXML (zip) en busca de macros y relaciones externas."""
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                nombres = zf.namelist()
                if any("vbaProject.bin" in n for n in nombres):
                    banderas.append(bandera("ADJ_MACRO", "vbaProject.bin en OOXML"))
                for nombre in nombres:
                    if not nombre.endswith(".rels"):
                        continue
                    contenido = zf.read(nombre).decode("utf-8", errors="replace")
                    if 'TargetMode="External"' in contenido:
                        banderas.append(
                            bandera("ADJ_ENLACE_EXTERNO", "relacion externa en OOXML")
                        )
                        break
        except (zipfile.BadZipFile, Exception) as exc:  # noqa: BLE001
            detalles.append(f"OOXML no parseable: {type(exc).__name__}")
            if not any(b.codigo == "ADJ_ARCHIVO_SOSPECHOSO" for b in banderas):
                banderas.append(bandera("ADJ_ARCHIVO_SOSPECHOSO", "OOXML zip no parseable"))

    def _analizar_ole2(
        self, payload: bytes, banderas: list[BanderaAdjunto], detalles: list[str]
    ) -> None:
        """Usa olevba para OLE2; degrada a sospechoso si falla (V.1)."""
        tiene_macro, tiene_enlace, detalle = self._analizador.analizar(payload)
        if detalle:
            detalles.append(detalle)
            if not any(b.codigo == "ADJ_ARCHIVO_SOSPECHOSO" for b in banderas):
                banderas.append(bandera("ADJ_ARCHIVO_SOSPECHOSO", "OLE2 no analizable"))
        if tiene_macro and not any(b.codigo == "ADJ_MACRO" for b in banderas):
            banderas.append(bandera("ADJ_MACRO", "macros VBA en OLE2"))
        if tiene_enlace and not any(b.codigo == "ADJ_ENLACE_EXTERNO" for b in banderas):
            banderas.append(bandera("ADJ_ENLACE_EXTERNO", "enlace externo en OLE2"))
