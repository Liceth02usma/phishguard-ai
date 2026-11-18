"""AC-AGT-05: al superar LLM_MAX_DIARIO, zona gris → revision_manual.

Se prueba en N-1 (modelo llamado), N (modelo llamado), N+1
(revision_manual sin llamar al modelo).
"""

from __future__ import annotations

from dobles_agente import ContadorDoble, ModeloDoble, entrada_agente_ejemplo


def test_tope_n_menos_1_llama_modelo() -> None:
    """Con N-1 llamadas, el modelo se invoca (aún hay cuota)."""
    modelo = ModeloDoble()
    contador = ContadorDoble(max_diario=3)
    entrada = entrada_agente_ejemplo(score=50)

    # Consumir N-1 = 2 llamadas
    contador.incrementar()
    contador.incrementar()

    from src.level2_agent.agente.agente import consultar_agente

    resultado = consultar_agente(entrada, modelo=modelo, contador=contador)  # type: ignore[arg-type]
    assert resultado.razon == "exito"
    assert resultado.llamadas_modelo >= 1
    assert len(modelo.llamadas) >= 1


def test_tope_n_llama_modelo() -> None:
    """Con N llamadas (justo en el límite), el modelo se invoca."""
    modelo = ModeloDoble()
    contador = ContadorDoble(max_diario=3)
    entrada = entrada_agente_ejemplo(score=50)

    # Consumir N = 3 llamadas
    contador.incrementar()
    contador.incrementar()
    contador.incrementar()

    from src.level2_agent.agente.agente import consultar_agente

    # N es el tope → disponible() retorna False
    assert not contador.disponible()
    resultado = consultar_agente(entrada, modelo=modelo, contador=contador)  # type: ignore[arg-type]
    assert resultado.razon == "tope_superado"
    assert resultado.llamadas_modelo == 0
    assert resultado.confirmacion_agente is None


def test_tope_n_mas_1_no_llama_modelo() -> None:
    """Con N+1 llamadas (tope superado), no se llama al modelo."""
    modelo = ModeloDoble()
    contador = ContadorDoble(max_diario=3)
    entrada = entrada_agente_ejemplo(score=50)

    # Consumir N+1 = 4 llamadas
    for _ in range(4):
        contador.incrementar()

    from src.level2_agent.agente.agente import consultar_agente

    resultado = consultar_agente(entrada, modelo=modelo, contador=contador)  # type: ignore[arg-type]
    assert resultado.razon == "tope_superado"
    assert resultado.llamadas_modelo == 0
    assert len(modelo.llamadas) == 0
    assert resultado.confirmacion_agente is None
