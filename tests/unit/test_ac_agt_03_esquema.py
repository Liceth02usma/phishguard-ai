"""AC-AGT-03: salida que no cumple el esquema → 1 reintento → revision_manual.

Si el modelo retorna JSON que no valida contra SalidaAgente, se reintenta
1 vez. Si persiste, ResultadoAgente.razon == "validacion_fallida" y
confirmacion_agente is None.
"""

from __future__ import annotations

from src.level2_agent.agente.modelos import ResultadoAgente

from dobles_agente import ModeloDobleInvalido, entrada_agente_ejemplo


def test_salida_invalidada_reintenta_una_vez() -> None:
    """Salida invalidada → 1 reintento → validacion_fallida."""
    modelo = ModeloDobleInvalido()
    entrada = entrada_agente_ejemplo(score=50)
    from src.level2_agent.agente.agente import consultar_agente

    resultado = consultar_agente(entrada, modelo=modelo)
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

    resultado = consultar_agente(entrada, modelo=modelo)
    assert resultado.reintentos == 2
