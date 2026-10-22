"""Conversión de HTML a texto limpio (FR-003, research D5).

Usa `html.parser.HTMLParser` de la biblioteca estándar (sin dependencias
externas). Elimina scripts, estilos, comentarios y texto oculto (display:none,
visibility:hidden, font-size:0, color igual al fondo); conserva el texto
visible de los enlaces. Función pura y determinista.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_ESTILO_OCULTO = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px)?\b",
    re.IGNORECASE,
)
_COLOR = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.IGNORECASE)
_FONDO = re.compile(r"(?:^|;)\s*(?:background-color|background)\s*:\s*([^;]+)", re.IGNORECASE)

_ETIQUETAS_IGNORADAS = frozenset({"script", "style"})


def _estilo_oculto(estilo: str) -> bool:
    """Detecta si un atributo `style` oculta el elemento."""
    if _ESTILO_OCULTO.search(estilo):
        return True
    color = _COLOR.search(estilo)
    fondo = _FONDO.search(estilo)
    if color and fondo:
        return color.group(1).strip().lower() == fondo.group(1).strip().lower()
    return False


class _ExtractorTexto(HTMLParser):
    """Extrae solo el texto visible de un documento HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._fragmentos: list[str] = []
        self._pila_oculta: list[bool] = []
        self._ignorando: int = 0

    @property
    def _oculto(self) -> bool:
        """True si algún elemento abierto oculta su contenido."""
        return any(self._pila_oculta)

    def _texto(self, contenido: str) -> None:
        if not self._oculto and self._ignorando == 0:
            trozo = contenido.strip()
            if trozo:
                self._fragmentos.append(trozo)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _ETIQUETAS_IGNORADAS:
            self._ignorando += 1
            self._pila_oculta.append(False)
            return
        if self._ignorando:
            self._pila_oculta.append(False)
            return
        estilo = next((v for k, v in attrs if k == "style" and v), "")
        oculto = bool(estilo) and _estilo_oculto(estilo)
        self._pila_oculta.append(oculto)

    def handle_endtag(self, tag: str) -> None:
        if tag in _ETIQUETAS_IGNORADAS and self._ignorando:
            self._ignorando -= 1
        if self._pila_oculta:
            self._pila_oculta.pop()

    def handle_data(self, data: str) -> None:
        self._texto(data)

    def handle_comment(self, data: str) -> None:
        """Los comentarios se descartan por completo (FR-003)."""

    def texto(self) -> str:
        """Devuelve el texto visible con el whitespace normalizado."""
        bruto = " ".join(self._fragmentos)
        bruto = re.sub(r"\s+", " ", bruto)
        return bruto.strip()


def html_a_texto(html: str) -> str:
    """Convierte HTML a texto visible limpio.

    Args:
        html: cadena de HTML (puede contener scripts, estilos y texto oculto).

    Returns:
        El texto visible sin scripts/estilos/comentarios/ocultos; cadena vacía
        si `html` es vacío. El HTML malformado no controlado devuelve lo
        parcialmente extraído en vez de lanzar (AC-NORM-06).
    """
    if not html:
        return ""
    extractor = _ExtractorTexto()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:
        return extractor.texto()
    return extractor.texto()
