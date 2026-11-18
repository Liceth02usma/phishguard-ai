"""AC-PER-05: la tasa de falsos positivos es nula cuando no hay
retroalimentación, y correcta cuando la hay."""

from __future__ import annotations

from src.level2_agent.persistencia.metricas import calcular_metricas

from dobles_persistencia import entrada_persistido_ejemplo


def test_tasa_fp_nula_sin_retroalimentacion() -> None:
    """Sin retroalimentación → tasa_falsos_positivos is None (I5)."""
    a1 = entrada_persistido_ejemplo(message_id="m1")
    a2 = entrada_persistido_ejemplo(message_id="m2")
    m = calcular_metricas([a1, a2])
    assert m.tasa_falsos_positivos is None


def test_tasa_fp_con_retroalimentacion() -> None:
    """Con retroalimentación → tasa_falsos_positivos calculada."""
    a1 = entrada_persistido_ejemplo(
        message_id="m1", retroalimentacion="falso_positivo"
    )
    a2 = entrada_persistido_ejemplo(
        message_id="m2", retroalimentacion="confirmado"
    )
    m = calcular_metricas([a1, a2])
    assert m.tasa_falsos_positivos is not None
    assert abs(m.tasa_falsos_positivos - 50.0) < 0.01


def test_tasa_fp_todos_falsos_positivos() -> None:
    """Todos falso_positivo → tasa 100%."""
    a1 = entrada_persistido_ejemplo(
        message_id="m1", retroalimentacion="falso_positivo"
    )
    a2 = entrada_persistido_ejemplo(
        message_id="m2", retroalimentacion="falso_positivo"
    )
    m = calcular_metricas([a1, a2])
    assert m.tasa_falsos_positivos is not None
    assert abs(m.tasa_falsos_positivos - 100.0) < 0.01


def test_tasa_fp_lista_vacia() -> None:
    """Lista vacía → tasa_falsos_positivos is None."""
    m = calcular_metricas([])
    assert m.tasa_falsos_positivos is None
