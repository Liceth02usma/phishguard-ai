"""Límites duros del correo (FR-004) y sus banderas (research D6, D7, D9).

Constantes nombradas: ningún umbral vive incrustado en el código (Art. III.6).
Función pura `evaluar_limites`: acota y decide la bandera sin efectos secundarios.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.level2_agent.models import Adjunto

LIMITE_BYTES_CORREO = 25 * 1024 * 1024
"""Tamaño máximo de la entrada en bytes (25 MiB; decisión D6)."""

LIMITE_CARACTERES_TEXTO = 20_000
"""Longitud máxima del texto que ve el modelo de lenguaje."""

LIMITE_URLS = 200
"""Cantidad máxima de URLs conservadas."""

LIMITE_ADJUNTOS = 20
"""Cantidad máxima de adjuntos conservados."""

LIMITE_NIVELES_MIME = 10
"""Profundidad máxima de partes MIME anidadas que se parsean."""

LIMITE_ASUNTO_LLM = 500
"""Cuota del asunto dentro del texto total que ve el modelo (Art. 0.6)."""

LIMITE_HEADERS_LLM = 4_000
"""Cuota de las cabeceras dentro del texto total que ve el modelo (Art. 0.6)."""

LIMITE_HTML_LLM = LIMITE_CARACTERES_TEXTO - LIMITE_ASUNTO_LLM - LIMITE_HEADERS_LLM
"""Cuota del HTML hacia el modelo: completa el tope de 20 000 chars (FR-004)."""

BANDERA_LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
"""Bandera que se registra al superar cualquier límite (nombre exigido por FR-004)."""

BANDERA_ENTRADA_DEGRADADA = "ENTRADA_DEGRADADA"
"""Bandera para entradas vacías o con codificación inválida (AC-NORM-06)."""

TEXTO_OCULTO_MARCADOR = "[NÚMERO_OCULTO]"
"""Marcador que sustituye a secuencias de 13 a 19 dígitos (FR-005)."""


@dataclass(frozen=True)
class ResultadoLimites:
    """Acotamiento resultante y bandera única por tipo (tabla D7).

    `bandera` es `None` cuando ningún límite se excede (en el valor justo en
    el límite NO hay bandera); si se excede uno o más, vale
    `BANDERA_LIMITE_EXCEDIDO` una sola vez (la lista no duplica entradas).
    """

    bandera: str | None
    texto_limpio: str
    urls: tuple[str, ...]
    adjuntos: tuple[Adjunto, ...]
    detalles: tuple[str, ...]


def _detectar_excesos(
    bytes_totales: int,
    texto: str,
    urls: Sequence[str],
    adjuntos: Sequence[Adjunto],
    profundidad: int,
) -> list[str]:
    """Devuelve una descripción por cada límite duro excedido (vacío si ninguno)."""
    detalles: list[str] = []
    if bytes_totales > LIMITE_BYTES_CORREO:
        detalles.append(f"correo de {bytes_totales} B excede {LIMITE_BYTES_CORREO} B")
    if len(texto) > LIMITE_CARACTERES_TEXTO:
        detalles.append(f"texto de {len(texto)} chars excede {LIMITE_CARACTERES_TEXTO}")
    if len(urls) > LIMITE_URLS:
        detalles.append(f"{len(urls)} URLs exceden {LIMITE_URLS}")
    if len(adjuntos) > LIMITE_ADJUNTOS:
        detalles.append(f"{len(adjuntos)} adjuntos exceden {LIMITE_ADJUNTOS}")
    if profundidad > LIMITE_NIVELES_MIME:
        detalles.append(f"profundidad MIME {profundidad} excede {LIMITE_NIVELES_MIME}")
    return detalles


def evaluar_limites(
    bytes_totales: int,
    texto: str,
    urls: Sequence[str],
    adjuntos: Sequence[Adjunto],
    profundidad: int,
) -> ResultadoLimites:
    """Aplica los cinco límites duros (FR-004): acota el contenido y decide la bandera.

    Args:
        bytes_totales: longitud en bytes de la entrada cruda.
        texto: texto limpio extraído (se trunca a ``LIMITE_CARACTERES_TEXTO``).
        urls: URLs extraídas (se conservan las primeras ``LIMITE_URLS``).
        adjuntos: adjuntos extraídos (se conservan los primeros ``LIMITE_ADJUNTOS``).
        profundidad: profundidad MIME máxima detectada en el recorrido.

    Returns:
        ResultadoLimites con el contenido acotado y la bandera (o ``None``).

    Raises:
        ValueError: si ``bytes_totales`` o ``profundidad`` son negativos.
    """
    if bytes_totales < 0 or profundidad < 0:
        raise ValueError("bytes_totales y profundidad no pueden ser negativos")

    detalles = _detectar_excesos(bytes_totales, texto, urls, adjuntos, profundidad)

    return ResultadoLimites(
        bandera=BANDERA_LIMITE_EXCEDIDO if detalles else None,
        texto_limpio=texto[:LIMITE_CARACTERES_TEXTO],
        urls=tuple(urls[:LIMITE_URLS]),
        adjuntos=tuple(adjuntos[:LIMITE_ADJUNTOS]),
        detalles=tuple(detalles),
    )
