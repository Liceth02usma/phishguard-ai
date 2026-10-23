"""Familia de dominios: distancia de edicion, homoglifos y punycode (spec 003).

``tldextract`` usa la PSL embebida (``suffix_list_urls=()``): sin red, determinista
(research D3). La comparacion de dominio parecido usa la distancia de Damerau-
Levenshtein (OSA) con umbral 2, calculada aqui (sin dependencias externas).
"""

from __future__ import annotations

import tldextract

from .modelos import (
    MAPA_HOMOGLIFOS,
    UMBRAL_DISTANCIA_EDICION,
    BanderaActivada,
    ContextoEvaluacion,
    EvaluadorBandera,
    dominio_de,
    fabricar_bandera,
    primer_valor,
)

# PSL embebida en el paquete: ninguna consulta a la red (Art. II.5, D3).
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())
_TRADUCCION = str.maketrans(MAPA_HOMOGLIFOS)


def distancia_edicion(a: str, b: str) -> int:
    """Distancia de Damerau-Levenshtein (OSA) entre dos cadenas (simetrica)."""
    len_a, len_b = len(a), len(b)
    d = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        d[i][0] = i
    for j in range(len_b + 1):
        d[0][j] = j
    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            costo = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + costo)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)  # transposicion
    return d[len_a][len_b]


def normalizar_dominio(d: str) -> str:
    """Minusculas, homoglifos→latino y sin punto final (research D6)."""
    return d.strip().lower().translate(_TRADUCCION).rstrip(".")


def dominio_organizacional(d: str) -> str:
    """Dominio registrable (etiqueta de registrador + TLD) vía PSL embebida."""
    ext = _EXTRACTOR(d)
    if ext.suffix and ext.domain:
        return f"{ext.domain}.{ext.suffix}"
    return ext.domain or d


class DominioParecido:
    """Dominio del remitente a distancia ≤2 de un dominio propio o marca (M03/FR-004)."""

    codigo = "DOMINIO_PARECIDO"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        valor = primer_valor(ctx.correo, "from")
        if valor is None:
            return None
        desde = dominio_de(valor)
        if desde is None:
            return None
        objetivo = normalizar_dominio(desde)
        candidatas = ctx.config.dominios_propios | ctx.config.marcas_protegidas
        for bruta in candidatas:
            cand = normalizar_dominio(bruta)
            if cand == objetivo:
                continue  # identico no es "parecido"
            dist = distancia_edicion(objetivo, cand)
            if 0 < dist <= UMBRAL_DISTANCIA_EDICION:
                return fabricar_bandera(
                    self.codigo, f"Dominio del remitente '{objetivo}' similar a '{cand}'"
                )
        return None


class DominioPunycode:
    """Dominio codificado en punycode (``xn--``), posible ofuscacion de punycode."""

    codigo = "DOMINIO_PUNYCODE"

    def evaluar(self, ctx: ContextoEvaluacion) -> BanderaActivada | None:
        valor = primer_valor(ctx.correo, "from")
        if valor is None:
            return None
        d = dominio_de(valor)
        if d and "xn--" in d:
            return fabricar_bandera(self.codigo, f"Dominio del remitente en punycode '{d}'")
        return None


REGISTRO_DOMINIOS: list[EvaluadorBandera] = [DominioParecido(), DominioPunycode()]
