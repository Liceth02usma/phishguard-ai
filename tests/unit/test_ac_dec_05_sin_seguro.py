"""AC-DEC-05: la palabra 'seguro' jamás aparece en la salida del motor.

FR-006 / Art. V.1: el veredicto final nunca declara un correo como
'seguro'. El catálogo de veredictos lo garantiza por construcción
(Literal sin 'seguro'), pero esta prueba lo verifica dinámicamente
sobre todos los campos de texto de VeredictoMotor.
"""

from __future__ import annotations

from src.level2_agent.decision.modelos import VeredictoMotor

from dobles_decision import entrada_ejemplo


def _verificar_sin_seguro(resultado: VeredictoMotor) -> None:
    """Verifica que ningún campo de texto contenga 'seguro'."""
    dump = resultado.model_dump()
    for clave, valor in dump.items():
        if isinstance(valor, str):
            assert "seguro" not in valor.lower(), (
                f"campo '{clave}' contiene 'seguro': {valor!r}"
            )
        elif isinstance(valor, list):
            for i, item in enumerate(valor):
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, str):
                            assert "seguro" not in v.lower(), (
                                f"{clave}[{i}].{k} contiene 'seguro': {v!r}"
                            )


def test_sin_seguro_veredicto_bajo() -> None:
    """Veredicto sin_indicadores no contiene 'seguro'."""
    entrada = entrada_ejemplo(score=10)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    _verificar_sin_seguro(resultado)
    assert resultado.veredicto != "seguro"


def test_sin_seguro_veredicto_sospechoso() -> None:
    """Veredicto sospechoso no contiene 'seguro'."""
    entrada = entrada_ejemplo(score=50)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    _verificar_sin_seguro(resultado)


def test_sin_seguro_veredicto_malicioso() -> None:
    """Veredicto malicioso no contiene 'seguro'."""
    entrada = entrada_ejemplo(score=80)
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    _verificar_sin_seguro(resultado)


def test_sin_seguro_veredicto_revision() -> None:
    """Veredicto revision_manual no contiene 'seguro'."""
    from src.level2_agent.decision.modelos import VerificacionIncompleta

    entrada = entrada_ejemplo(
        score=10,
        verificaciones_incompletas=[
            VerificacionIncompleta(tipo="vt_adjunto", razon="VT_NO_DISPONIBLE"),
        ],
    )
    from src.level2_agent.decision.motor import evaluar_veredicto

    resultado = evaluar_veredicto(entrada)
    _verificar_sin_seguro(resultado)


def test_tipo_veredicto_no_tiene_seguro() -> None:
    """El tipo Literal Veredicto no incluye 'seguro' como valor posible."""
    # Verificación estática: el tipo Veredicto es Literal sin 'seguro'
    from src.level2_agent.decision.modelos import Veredicto
    from typing import get_args

    valores = get_args(Veredicto)
    assert "seguro" not in valores
