"""AC-AGT-03: salida que no cumple el esquema â†’ 1 reintento â†’ revision_manual.

Si el modelo retorna JSON que no valida contra SalidaAgente, se reintenta
1 vez. Si persiste, ResultadoAgente.razon == "validacion_fallida" y
confirmacion_agente is None.
"""

from __future__ import annotations

from dobles_agente import (
    ContadorDoble,
    ModeloDobleInvalido,
    entrada_agente_ejemplo,
)


def test_salida_invalidada_reintenta_una_vez() -> None:
    """Salida invalidada â†’ 1 reintento â†’ validacion_fallida."""
    modelo = ModeloDobleInvalido()
    entrada = entrada_agente_ejemplo(score=50)
    from src.level2_agent.agente.agente import consultar_agente

    # Contador aislado (auditorÃ­a): sin Ã©l, el tope diario real de MongoDB
    # (llm_contador) condicionaba el resultado de esta prueba.
    resultado = consultar_agente(
        entrada, modelo=modelo, contador=ContadorDoble()  # type: ignore[arg-type]
    )
    assert resultado.razon == "validacion_fallida"
    assert resultado.confirmacion_agente is None
    assert resultado.salida is None
    # El modelo fue llamado 2 veces (primer intento + reintento)
    assert resultado.llamadas_modelo == 2
    assert len(modelo.llamadas) == 2


def test_salida_invalidada_reintentos_2() -> None:
    """ResultadoAgente.reintentos == 2 tras fallar primer intento y reintento."""
    modelo = ModeloDobleInvalido()
    entrada = entrada_agente_ejemplo(score=50)
    from src.level2_agent.agente.agente import consultar_agente

    resultado = consultar_agente(
        entrada, modelo=modelo, contador=ContadorDoble()  # type: ignore[arg-type]
    )
    assert resultado.reintentos == 2
