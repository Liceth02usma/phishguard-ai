"""Extracción de candidatas de URL desde HTML y texto (FR-001, research D2).

Los pares (texto del enlace, destino) alimentan `URL_TEXTO_DISTINTO_DESTINO`;
`src`/`action` y el texto plano aportan candidatas adicionales (M04b).
`normalizacion/extraccion.py` de la spec 002 NO se modifica (research D2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

# URL absoluta http/https en texto libre (texto plano y texto de enlaces).
_URL_PATRON = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
# Atributos HTML que transportan URL (FR-001).
_ATRIBUTOS_URL = ("href", "src", "action")
_ESQUEMAS_OK = ("http://", "https://")


@dataclass(frozen=True)
class Candidata:
    """Candidata cruda: URL tal cual aparece y su texto mostrado, si lo tiene."""

    url: str
    texto: str = ""


class _ExtractorHTML(HTMLParser):
    """Extrae pares (texto, destino) de enlaces y URL de `src`/`action`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pares: list[Candidata] = []
        self.atributos: list[Candidata] = []
        self._href_actual: str | None = None
        self._texto_enlace: list[str] = []

    def handle_starttag(self, etiqueta: str, atributos: list[tuple[str, str | None]]) -> None:
        """Registra href (abre par), src y action (candidatas sueltas)."""
        mapa = {clave.lower(): valor for clave, valor in atributos if valor}
        for nombre in _ATRIBUTOS_URL:
            valor = mapa.get(nombre)
            if not valor or not valor.lower().startswith(_ESQUEMAS_OK):
                continue
            if nombre == "href":
                self._href_actual = valor
                self._texto_enlace = []
            else:
                self.atributos.append(Candidata(url=valor))

    def handle_data(self, dato: str) -> None:
        """Acumula el texto visible mientras se está dentro de un enlace."""
        if self._href_actual is not None:
            self._texto_enlace.append(dato)

    def handle_endtag(self, etiqueta: str) -> None:
        """Cierra el par (texto, destino) al terminar el `<a>`."""
        if etiqueta == "a" and self._href_actual is not None:
            texto = "".join(self._texto_enlace).strip()
            self.pares.append(Candidata(url=self._href_actual, texto=texto))
            self._href_actual = None
            self._texto_enlace = []


def _de_texto(bloque: str) -> list[Candidata]:
    """Candidatas http/https de un bloque de texto libre."""
    return [Candidata(url=coincidencia.group(0)) for coincidencia in _URL_PATRON.finditer(bloque)]


def extraer_candidatas(html: str, texto: str) -> list[Candidata]:
    """Extrae todas las candidatas en orden: pares de enlaces, `src`/`action`,
    URL mostradas en el texto de los enlaces y URL en texto plano (M04b)."""
    salida: list[Candidata] = []
    if html:
        parser = _ExtractorHTML()
        try:
            parser.feed(html)
            parser.close()
        except (AssertionError, ValueError, RecursionError):
            # HTMLHostil arbitrario (AC-URL-07): degradamos a solo texto.
            parser.pares.clear()
            parser.atributos.clear()
        salida.extend(parser.pares)
        salida.extend(parser.atributos)
        for par in parser.pares:
            # La URL mostrada dentro del texto de un enlace también es candidata.
            salida.extend(_de_texto(par.texto))
    if texto:
        salida.extend(_de_texto(texto))
    return salida
