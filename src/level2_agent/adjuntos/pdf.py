"""Detección de acciones peligrosas en PDF (FR-004).

`pypdf` de solo lectura + escaneo crudo de `/JavaScript`, `/OpenAction` y
`/Launch` (defensa en profundidad, research D7). PDF no parseable →
`ADJ_ARCHIVO_SOSPECHOSO` (V.1).
"""

from __future__ import annotations

import io

from src.level2_agent.adjuntos.modelos import (
    BanderaAdjunto,
    ContextoAdjunto,
    ResultadoDetector,
    bandera,
)

_TOKENS_PDF = (b"/JavaScript", b"/OpenAction", b"/Launch")
_EXT_PDF = frozenset({"pdf"})


class PdfDetector:
    """Detector de acciones peligrosas en PDF (FR-004)."""

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        ext = ctx.extension_final.lower().lstrip(".")
        es_pdf = ext in _EXT_PDF or ctx.tipo_real == "pdf"
        if not es_pdf:
            return ResultadoDetector((), ())

        payload = ctx.payload
        banderas: list[BanderaAdjunto] = []
        detalles: list[str] = []

        encontrado_crudo = self._escaneo_crudo(payload)
        encontrado_pypdf, fallo_pypdf = self._caminata_pypdf(payload)

        if (encontrado_crudo or encontrado_pypdf) and not any(
            b.codigo == "ADJ_PDF_ACTIVO" for b in banderas
        ):
            banderas.append(bandera("ADJ_PDF_ACTIVO", "accion peligrosa en PDF"))

        if fallo_pypdf and not (encontrado_crudo or encontrado_pypdf):
            banderas.append(bandera("ADJ_ARCHIVO_SOSPECHOSO", "PDF no parseable"))
            detalles.append("pypdf no pudo parsear el PDF")

        return ResultadoDetector(tuple(banderas), tuple(detalles))

    def _escaneo_crudo(self, payload: bytes) -> bool:
        """Escanea bytes crudos por tokens peligrosos (defensa en profundidad)."""
        return any(token in payload for token in _TOKENS_PDF)

    def _caminata_pypdf(self, payload: bytes) -> tuple[bool, bool]:
        """Recorre el PDF con pypdf; devuelve (encontrado, fallo)."""
        if not payload:
            return (False, True)
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(payload), strict=False)
            root = reader.trailer.get("/Root", {})
            encontrado = False
            if "/OpenAction" in root:
                encontrado = True
            if "/Names" in root:
                names = root["/Names"]
                if "/JavaScript" in names:
                    encontrado = True
            for pagina in reader.pages:
                if "/AA" in pagina:
                    encontrado = True
                    break
            return (encontrado, False)
        except Exception:  # noqa: BLE001 — degrada a sospechoso (D14)
            return (False, True)
