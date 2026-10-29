"""Reglas duras del motor de decisión (spec 008, M09).

Cada regla es un callable que recibe EntradaMotor y retorna ReglaAplicada
si aplica, o None si no. Se evalúan en orden R1→R5; la primera que
aplica fija veredicto='malicioso' (FR-001).

Art. VI.2: las condiciones son LITERALES de M09; no se inventan reglas.
"""

from __future__ import annotations

from src.level2_agent.decision.modelos import (
    DESCRIPCION_REGLA,
    SEVERIDAD_REGLA,
    EntradaMotor,
    IdRegla,
    ReglaAplicada,
)


def _r1(entrada: EntradaMotor) -> ReglaAplicada | None:
    """R1: algún hash de adjunto con clasificación VT maliciosa."""
    for vt in entrada.resultados_vt:
        if vt.tipo == "archivo" and vt.clasificacion == "maliciosa":
            return ReglaAplicada(
                id="R1",
                severidad=SEVERIDAD_REGLA["R1"],
                descripcion=DESCRIPCION_REGLA["R1"],
            )
    return None


def _r2(entrada: EntradaMotor) -> ReglaAplicada | None:
    """R2: alguna URL con clasificación VT maliciosa."""
    for vt in entrada.resultados_vt:
        if vt.tipo == "url" and vt.clasificacion == "maliciosa":
            return ReglaAplicada(
                id="R2",
                severidad=SEVERIDAD_REGLA["R2"],
                descripcion=DESCRIPCION_REGLA["R2"],
            )
    return None


def _r3(entrada: EntradaMotor) -> ReglaAplicada | None:
    """R3: dominio del remitente con clasificación VT maliciosa."""
    for vt in entrada.resultados_vt:
        if vt.tipo == "dominio" and vt.clasificacion == "maliciosa":
            return ReglaAplicada(
                id="R3",
                severidad=SEVERIDAD_REGLA["R3"],
                descripcion=DESCRIPCION_REGLA["R3"],
            )
    return None


def _r4(entrada: EntradaMotor) -> ReglaAplicada | None:
    """R4: SPF=fail Y DKIM=fail Y DMARC=fail Y (dominio parecido O nombre suplanta)."""
    auth = entrada.estados_autenticacion
    if auth.spf != "fail" or auth.dkim != "fail" or auth.dmarc != "fail":
        return None
    # Verificar si hay bandera de dominio parecido o nombre que suplanta
    codigos = {b.codigo for b in entrada.banderas_cabeceras}
    if "DOMINIO_PARECIDO" in codigos or "NOMBRE_SUPLANTA" in codigos:
        return ReglaAplicada(
            id="R4",
            severidad=SEVERIDAD_REGLA["R4"],
            descripcion=DESCRIPCION_REGLA["R4"],
        )
    return None


def _r5(entrada: EntradaMotor) -> ReglaAplicada | None:
    """R5: adjunto de macro/ejecutable en archivo cifrado, remitente no autenticado."""
    # Remitente autenticado → R5 no aplica
    auth = entrada.estados_autenticacion
    if auth.spf == "pass" or auth.dkim == "pass":
        return None
    # Buscar adjunto con macro/ejecutivo Y cifrado con contraseña
    codigos_riesgo = {"ADJ_MACRO", "ADJ_EXTENSION_RIESGO"}
    for adj in entrada.resultado_adjuntos:
        tiene_riesgo = any(b.codigo in codigos_riesgo for b in adj.banderas)
        es_cifrado = "cifrado_con_contrasena" in adj.detalles
        if tiene_riesgo and es_cifrado:
            return ReglaAplicada(
                id="R5",
                severidad=SEVERIDAD_REGLA["R5"],
                descripcion=DESCRIPCION_REGLA["R5"],
            )
    return None


# --- Lista ordenada de reglas duras (Chain of Responsibility, research D3) ---

REGLAS_DURAS: list[tuple[IdRegla, type]] = [
    ("R1", type(_r1)),  # noqa: FURB113 — estructura explícita para trazabilidad
    ("R2", type(_r2)),
    ("R3", type(_r3)),
    ("R4", type(_r4)),
    ("R5", type(_r5)),
]
"""Orden de evaluación: R1→R5. La primera que aplica fija malicioso."""


def evaluar_reglas_duras(entrada: EntradaMotor) -> list[ReglaAplicada]:
    """Evalúa las reglas duras en orden; retorna las que aplicaron.

    En práctica, solo la primera que aplica importa (FR-001: la primera
    fija malicioso). Pero retornamos todas las que aplican para
    trazabilidad y explicabilidad.
    """
    aplicadas: list[ReglaAplicada] = []
    for fn in (_r1, _r2, _r3, _r4, _r5):
        resultado = fn(entrada)
        if resultado is not None:
            aplicadas.append(resultado)
            break  # FR-001: la primera que aplica fija el veredicto
    return aplicadas
