"""Detección de tipo real por firma (magic bytes) y comparación (FR-002).

Usa `filetype` (pure Python, sin dependencias nativas — research D3) para
detectar el tipo real. La bandera `ADJ_TIPO_NO_COINCIDE` se activa solo
con firma concluyente (research D5).
"""

from __future__ import annotations

import filetype
from src.level2_agent.adjuntos.modelos import (
    BanderaAdjunto,
    ContextoAdjunto,
    ResultadoDetector,
    bandera,
)

# Magia OLE2 (Compound File Binary) — filetype no siempre la detecta.
_MAGIA_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def detectar_por_firma(payload: bytes) -> str:
    """Detecta el tipo real por magic bytes (FR-002).

    Returns:
        Extensión del tipo detectado (ej. ``"pdf"``, ``"zip"``, ``"exe"``) o
        ``"desconocido"`` si no hay firma concluyente (research D5).
    """
    if not payload:
        return "desconocido"
    ft = filetype.guess(payload)
    if ft is not None:
        return str(ft.extension)
    if payload.startswith(_MAGIA_OLE2):
        return "ole2"
    return "desconocido"


def _familia(extension: str) -> str:
    """Mapea una extensión a una familia para comparar tipo real vs declarado."""
    ext = extension.lower().lstrip(".")
    if ext == "pdf":
        return "pdf"
    if ext in {"zip", "docx", "xlsx", "pptx", "odt", "ods", "odp"}:
        return "zip"
    if ext in {"exe", "scr", "com", "msi", "dll"}:
        return "ejecutable"
    if ext in {"png", "jpg", "jpeg", "gif", "bmp"}:
        return "imagen"
    if ext in {"doc", "xls", "ppt", "ole2"}:
        return "office-ole"
    if ext in {"html", "htm", "svg"}:
        return "html"
    return "otro"


def _familia_mime(tipo_declarado: str) -> str:
    """Mapea un Content-Type a una familia (``"otro"`` si es genérico)."""
    mime = tipo_declarado.lower().strip()
    if mime in {"application/pdf"}:
        return "pdf"
    if mime in {"application/zip", "application/x-zip-compressed"} or mime.startswith(
        "application/vnd.openxmlformats"
    ):
        return "zip"
    if mime in {"application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint"}:
        return "office-ole"
    if mime.startswith("image/"):
        return "imagen"
    if mime in {"text/html", "application/xhtml+xml"}:
        return "html"
    if mime in {"application/x-dosexec", "application/x-msdownload"}:
        return "ejecutable"
    return "otro"


class FirmaDetector:
    """Detector de discrepancia entre tipo real y extensión/Content-Type (FR-002)."""

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        """Activa ``ADJ_TIPO_NO_COINCIDE`` solo con firma concluyente (D5)."""
        if ctx.tipo_real == "desconocido":
            return ResultadoDetector((), ())

        familia_real = _familia(ctx.tipo_real)
        if familia_real == "otro":
            return ResultadoDetector((), ())

        banderas: list[BanderaAdjunto] = []
        detalles: list[str] = []

        familia_ext = _familia(ctx.extension_final)
        if familia_real != familia_ext:
            banderas.append(
                bandera(
                    "ADJ_TIPO_NO_COINCIDE",
                    f"firma {ctx.tipo_real}, extension .{ctx.extension_final}",
                )
            )

        if ctx.tipo_declarado:
            familia_mime = _familia_mime(ctx.tipo_declarado)
            if familia_mime != "otro" and familia_real != familia_mime and not banderas:
                banderas.append(
                    bandera(
                        "ADJ_TIPO_NO_COINCIDE",
                        f"firma {ctx.tipo_real}, content-type {ctx.tipo_declarado}",
                    )
                )

        return ResultadoDetector(tuple(banderas), tuple(detalles))
