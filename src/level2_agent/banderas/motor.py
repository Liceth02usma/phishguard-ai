"""Motor de banderas: compone las 5 familias, ordena por catalogo y aplica el tope (spec 003)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.level2_agent.models import EmailData

from .autenticacion import REGISTRO_AUTENTICACION, calcular_autenticacion
from .configuracion import ConfigBanderas
from .contexto import REGISTRO_CONTEXTO
from .dominios import REGISTRO_DOMINIOS
from .identidad import REGISTRO_IDENTIDAD
from .modelos import (
    TOPE_PUNTOS_BANDERAS,
    BanderaActivada,
    ContextoEvaluacion,
    EvaluadorBandera,
    ResultadoBanderas,
    orden_de_catalogo,
)
from .rdap import REGISTRO_RDAP, ClienteRDAP, RequestsRDAP, cache_proceso, crear_consultor_rdap

REGISTRO: list[EvaluadorBandera] = [
    *REGISTRO_AUTENTICACION,
    *REGISTRO_IDENTIDAD,
    *REGISTRO_DOMINIOS,
    *REGISTRO_CONTEXTO,
    *REGISTRO_RDAP,
]
"""Las 16 estrategias del catalogo 5.1, una por bandera (Strategy + Registry, D2)."""


def calcular_puntos(banderas: list[BanderaActivada]) -> int:
    """Suma de puntos con tope de 60 (AC-HDR-05)."""
    return min(sum(b.puntos for b in banderas), TOPE_PUNTOS_BANDERAS)


def evaluar_banderas(
    correo: EmailData,
    config: ConfigBanderas | None = None,
    ahora: datetime | None = None,
    cliente_rdap: ClienteRDAP | None = None,
) -> ResultadoBanderas:
    """Evalua las 16 banderas de un ``EmailData`` y devuelve el resultado consolidado.

    Determinista y sin red en las pruebas: ``ahora`` y ``cliente_rdap`` se inyectan
    (Art. II.5). Sin ``cliente_rdap`` usa ``RequestsRDAP`` (produccion).
    """
    cfg = config if config is not None else ConfigBanderas()
    momento = ahora if ahora is not None else datetime.now(UTC)
    rdap: ClienteRDAP = cliente_rdap if cliente_rdap is not None else RequestsRDAP()
    consultor = crear_consultor_rdap(rdap, cache_proceso(), momento)
    autenticacion = calcular_autenticacion(cfg, correo.cabeceras)
    ctx = ContextoEvaluacion(
        correo=correo,
        config=cfg,
        ahora=momento,
        autenticacion=autenticacion,
        consultar_fecha_registro=consultor,
    )
    activadas: list[BanderaActivada] = []
    for evaluador in REGISTRO:
        banda = evaluador.evaluar(ctx)
        if banda is not None:
            activadas.append(banda)
    activadas.sort(key=lambda b: orden_de_catalogo(b.codigo))
    return ResultadoBanderas(
        banderas=activadas,
        estados_autenticacion=autenticacion.estados,
        puntos_totales=calcular_puntos(activadas),
    )
