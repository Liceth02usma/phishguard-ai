"""Motor del análisis de adjuntos: orquesta los detectores (spec 005).

`analizar_adjunto` es la API pública: construye el contexto, calcula hashes,
detecta el tipo real y ejecuta el registry de detectores en orden. Nunca
lanza por datos de entrada (D14, AC-ADJ-06).
"""

from __future__ import annotations

from src.level2_agent.adjuntos.comprimidos import ComprimidosDetector
from src.level2_agent.adjuntos.configuracion import ConfigAdjuntos
from src.level2_agent.adjuntos.extensiones import ExtensionesDetector
from src.level2_agent.adjuntos.firma import FirmaDetector, detectar_por_firma
from src.level2_agent.adjuntos.hashes import calcular_hashes
from src.level2_agent.adjuntos.modelos import (
    CATALOGO_ADJUNTOS,
    AnalisisAdjunto,
    BanderaAdjunto,
    ContextoAdjunto,
    Detector,
    ResultadoDetector,
    bandera,
)
from src.level2_agent.adjuntos.office import OfficeDetector
from src.level2_agent.adjuntos.pdf import PdfDetector

# Orden del catálogo 5.3 para ordenar banderas estables.
_ORDEN_CATALOGO: dict[str, int] = {cod: i for i, cod in enumerate(CATALOGO_ADJUNTOS)}


def _split_extensiones(nombre: str) -> tuple[str, tuple[str, ...]]:
    """Separa la extensión final y las previas (sin os.path, D14).

    Returns:
        (extension_final, extensiones_previas) en minúsculas, sin punto.
    """
    base, sep, ext = nombre.rpartition(".")
    if not sep:
        return ("", ())
    previas: list[str] = []
    resto = base
    while "." in resto:
        resto, _, e = resto.rpartition(".")
        if e:
            previas.append(e.lower())
    return (ext.lower(), tuple(reversed(previas)))


def _registry() -> list[Detector]:
    """Lista ordenada de detectores (Strategy + Registry, research D2)."""
    return [
        FirmaDetector(),
        ExtensionesDetector(),
        OfficeDetector(),
        PdfDetector(),
        ComprimidosDetector(),
    ]


def analizar_adjunto(
    nombre: str,
    tipo_declarado: str,
    payload: bytes,
    config: ConfigAdjuntos | None = None,
) -> AnalisisAdjunto:
    """Analiza estáticamente un adjunto en memoria (FR-001..FR-006).

    Nunca escribe a disco, nunca ejecuta, nunca usa red. Nunca lanza por
    datos de entrada (AC-ADJ-06, D14).
    """
    if config is None:
        config = ConfigAdjuntos.defecto()

    sha256, md5, sha1 = calcular_hashes(payload)
    tipo_real = detectar_por_firma(payload)
    extension_final, extensiones_previas = _split_extensiones(nombre)

    ctx = ContextoAdjunto(
        nombre=nombre,
        extension_final=extension_final,
        extensiones_previas=extensiones_previas,
        tipo_real=tipo_real,
        tipo_declarado=tipo_declarado,
        payload=payload,
        config=config,
    )

    todas_banderas: list[BanderaAdjunto] = []
    todos_detalles: list[str] = []

    for detector in _registry():
        try:
            resultado = detector.evaluar(ctx)
        except Exception as exc:  # noqa: BLE001 — seguridad: motor nunca lanza (D14)
            resultado = ResultadoDetector(
                (bandera("ADJ_ARCHIVO_SOSPECHOSO", f"detector fallo: {type(exc).__name__}"),),
                (f"detector {type(detector).__name__} fallo: {exc}",),
            )
        todas_banderas.extend(resultado.banderas)
        todos_detalles.extend(resultado.detalles)

    # Deduplicar por código (primera ocurrencia) y ordenar por catálogo.
    vistas: set[str] = set()
    unicas: list[BanderaAdjunto] = []
    for b in todas_banderas:
        if b.codigo not in vistas:
            vistas.add(b.codigo)
            unicas.append(b)
    unicas.sort(key=lambda b: _ORDEN_CATALOGO[b.codigo])

    return AnalisisAdjunto(
        nombre=nombre,
        tipo_declarado=tipo_declarado,
        tipo_real=tipo_real,
        tamano_bytes=len(payload),
        sha256=sha256,
        md5=md5,
        sha1=sha1,
        banderas=unicas,
        detalles=todos_detalles,
    )
