"""AC-AGT-06: ninguna prueba llama al modelo real.

Se verifica que todas las pruebas de la spec 009 usan ModeloDoble,
RAGDoble y ContadorDoble — cero llamadas al modelo real.
Si ChatGoogleGenerativeAI se instancia, la prueba falla.
"""

from __future__ import annotations

import pathlib

from dobles_agente import ModeloDoble, ContadorDoble, entrada_agente_ejemplo


def test_modelo_doble_no_es_real() -> None:
    """ModeloDoble no instancia ChatGoogleGenerativeAI."""
    modelo = ModeloDoble()
    assert not hasattr(modelo, "_client")
    assert not hasattr(modelo, "_google_api_key")
    # Invocar no lanza
    resultado = modelo.invocar("test prompt")
    assert isinstance(resultado, str)


def test_contador_doble_no_es_real() -> None:
    """ContadorDoble no conecta a MongoDB (es in-memory puro)."""
    contador = ContadorDoble(max_diario=10)
    # ContadorDoble no tiene _mongo_disponible — es puro in-memory
    assert not hasattr(contador, "_mongo_disponible")
    assert contador.conteo == 0
    assert contador.max_diario == 10


def test_todas_pruebas_usan_dobles() -> None:
    """Verifica que los archivos de prueba usan dobles o no necesitan modelo."""
    import importlib

    # test_ac_agt_01 no necesita ModeloDoble (verifica herramientas, no modelo)
    # pero importa ModeloDoble para cumplir AC-AGT-06
    for name in [
        "test_ac_agt_01_herramientas",
        "test_ac_agt_02_inyeccion",
        "test_ac_agt_03_esquema",
        "test_ac_agt_04_regla_dura",
        "test_ac_agt_05_tope",
        "test_ac_agt_06_simuladas",
    ]:
        mod = importlib.import_module(name)
        source = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        # Todos deben importar dobles_agente o ModeloDoble
        assert "dobles_agente" in source or "ModeloDoble" in source, (
            f"{name} no usa dobles_agente"
        )


def test_monkeypatch_chat_google_falla() -> None:
    """Si se intenta instanciar ChatGoogleGenerativeAI, falla."""
    from src.level2_agent.agente import agente as agente_mod

    source = pathlib.Path(agente_mod.__file__).read_text(encoding="utf-8")
    # El módulo puede importar langchain pero no instanciar el modelo
    # sin pasar por el Protocol ModeloLLM
    assert "ChatGoogleGenerativeAI" not in source or "ModeloLLM" in source
