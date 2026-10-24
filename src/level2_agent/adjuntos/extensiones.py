"""Detección de extensiones de riesgo, doble extensión y HTML/SVG (FR-003).

Reglas puras sobre el nombre del adjunto (research D4). La extensión que
manda es la última; los espacios antes de la extensión activan
``ADJ_DOBLE_EXTENSION`` (M05).
"""

from __future__ import annotations

import re

from src.level2_agent.adjuntos.modelos import (
    BanderaAdjunto,
    ContextoAdjunto,
    ResultadoDetector,
    bandera,
)

# Espacios en blanco justo antes de la extensión final (M05: "espacios antes
# de la extensión" → ADJ_DOBLE_EXTENSION).
_ESPACIO_PRE_EXT = re.compile(r"\s+\.[^.]+$")


class ExtensionesDetector:
    """Detector de extensiones de riesgo, doble extensión y HTML/SVG (FR-003)."""

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        cfg = ctx.config
        ext = ctx.extension_final.lower().lstrip(".")
        banderas: list[BanderaAdjunto] = []

        es_riesgo = ext in cfg.extensiones_riesgo
        es_html = ext in cfg.extensiones_html

        if es_html:
            banderas.append(bandera("ADJ_HTML", f"extension .{ext} es HTML/SVG"))
        elif es_riesgo:
            banderas.append(
                bandera("ADJ_EXTENSION_RIESGO", f"extension .{ext} es de riesgo")
            )

        # Doble extensión: extensión final de riesgo/html + extensión anterior
        # documental o de riesgo (factura.pdf.exe).
        if (es_riesgo or es_html) and ctx.extensiones_previas:
            for prev in ctx.extensiones_previas:
                prev_limpia = prev.lower().lstrip(".")
                if (
                    prev_limpia in cfg.extensiones_documental
                    or prev_limpia in cfg.extensiones_riesgo
                ):
                    banderas.append(
                        bandera(
                            "ADJ_DOBLE_EXTENSION",
                            f"extension .{prev_limpia} antes de .{ext}",
                        )
                    )
                    break

        # Espacios antes de la extensión final (M05).
        if _ESPACIO_PRE_EXT.search(ctx.nombre) and not any(
            b.codigo == "ADJ_DOBLE_EXTENSION" for b in banderas
        ):
                banderas.append(
                    bandera(
                        "ADJ_DOBLE_EXTENSION",
                        "espacios antes de la extension final",
                    )
                )

        return ResultadoDetector(tuple(banderas), ())
