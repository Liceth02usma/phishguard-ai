"""Saneado de URLs antes de cualquier consulta externa (FR-007, Art. V.4, D12).

Elimina los 7 parámetros sensibles literales de la FR-007 (`token`, `key`,
`session`, `email`, `user`, `code`, `password`) y cualquier parámetro cuyo
valor tenga forma de correo. Función pura: la URL original nunca se muta.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.level2_agent.analisis_urls.configuracion import ConfigURLs

# Valor con forma de dirección de correo (AC-URL-06).
_CORREO_PATRON = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _valor_sensible(valor: str) -> bool:
    """True si el valor tiene forma de correo: se elimina sin importar el nombre."""
    return bool(_CORREO_PATRON.match(valor))


def sanitizar_parametros(url: str, config: ConfigURLs) -> str:
    """Devuelve la URL sin parámetros sensibles ni valores con forma de correo.

    Es el ÚNICO formato que puede cruzar hacia puertos externos (FR-007,
    invariante I3). Si la URL es irresoluble, se devuelve tal cual.
    """
    try:
        partes = urlsplit(url)
        if not partes.query:
            return url
        parametros = parse_qsl(partes.query, keep_blank_values=True)
    except ValueError:
        return url
    conservados = [
        (clave, valor)
        for clave, valor in parametros
        if clave.lower() not in config.parametros_sensibles and not _valor_sensible(valor)
    ]
    if len(conservados) == len(parametros):
        return url
    return urlunsplit(
        (partes.scheme, partes.netloc, partes.path, urlencode(conservados), partes.fragment)
    )
