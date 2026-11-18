"""Tests del patrón Strategy + Adapter para multi-proveedor LLM.

Factory: crear_modelo(proveedor) → ModeloLLM
Adapters: SimuladoAdapter, GeminiAdapter, GroqAdapter
"""

from __future__ import annotations

import os

import pytest
from src.level2_agent.agente.modelos import SalidaAgente

# --- Factory tests ---


class TestFactory:
    """Tests de la factory crear_modelo (Strategy)."""

    def test_crear_simulado(self) -> None:
        """crear_modelo("simulado") retorna SimuladoAdapter."""
        from src.level2_agent.agente.factory import crear_modelo
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        modelo = crear_modelo("simulado")
        assert isinstance(modelo, SimuladoAdapter)

    def test_crear_gemini(self) -> None:
        """crear_modelo("gemini") retorna GeminiAdapter."""
        from src.level2_agent.agente.factory import crear_modelo
        from src.level2_agent.agente.gemini_adapter import GeminiAdapter

        modelo = crear_modelo("gemini")
        assert isinstance(modelo, GeminiAdapter)

    def test_crear_groq(self) -> None:
        """crear_modelo("groq") retorna GroqAdapter."""
        from src.level2_agent.agente.factory import crear_modelo
        from src.level2_agent.agente.groq_adapter import GroqAdapter

        modelo = crear_modelo("groq")
        assert isinstance(modelo, GroqAdapter)

    def test_proveedor_desconocido_lanza_error(self) -> None:
        """crear_modelo con proveedor desconocido → ValueError."""
        from src.level2_agent.agente.factory import crear_modelo

        with pytest.raises(ValueError, match="Proveedor desconocido"):
            crear_modelo("openai")  # type: ignore[arg-type]

    def test_env_var_llm_proveedor(self) -> None:
        """crear_modelo() lee LLM_PROVEEDOR del entorno."""
        from src.level2_agent.agente.factory import crear_modelo
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        os.environ["LLM_PROVEEDOR"] = "simulado"
        try:
            modelo = crear_modelo()
            assert isinstance(modelo, SimuladoAdapter)
        finally:
            del os.environ["LLM_PROVEEDOR"]

    def test_env_var_invalida_lanza_error(self) -> None:
        """LLM_PROVEEDOR inválido → ValueError."""
        from src.level2_agent.agente.factory import crear_modelo

        os.environ["LLM_PROVEEDOR"] = "no_existe"
        try:
            with pytest.raises(ValueError, match="Proveedor desconocido"):
                crear_modelo()
        finally:
            del os.environ["LLM_PROVEEDOR"]

    def test_default_es_gemini(self) -> None:
        """Sin LLM_PROVEEDOR, el default es gemini."""
        from src.level2_agent.agente.factory import crear_modelo
        from src.level2_agent.agente.gemini_adapter import GeminiAdapter

        os.environ.pop("LLM_PROVEEDOR", None)
        modelo = crear_modelo()
        assert isinstance(modelo, GeminiAdapter)


# --- SimuladoAdapter tests ---


class TestSimuladoAdapter:
    """Tests del adapter simulado."""

    def test_invocar_retorna_json_valido(self) -> None:
        """SimuladoAdapter.invocar() retorna JSON válido."""
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        adapter = SimuladoAdapter()
        resultado = adapter.invocar("test prompt")
        # Debe ser parseable como SalidaAgente
        salida = SalidaAgente.model_validate_json(resultado)
        assert salida.es_phishing is False

    def test_invocar_registra_llamada(self) -> None:
        """SimuladoAdapter registra las llamadas."""
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        adapter = SimuladoAdapter()
        adapter.invocar("prompt1")
        adapter.invocar("prompt2")
        assert len(adapter.llamadas) == 2
        assert adapter.llamadas[0] == "prompt1"

    def test_salida_personalizada(self) -> None:
        """SimuladoAdapter con salida personalizada."""
        from src.level2_agent.agente.simulado_adapter import SimuladoAdapter

        salida_custom = SalidaAgente(
            resumen="Custom",
            analisis_tecnico="Custom tech",
            es_phishing=True,
            indicadores_phishing=["test"],
            nivel_severidad="Alto",
            justificacion_veredicto="Custom just",
        )
        adapter = SimuladoAdapter(salida=salida_custom)
        resultado = adapter.invocar("test")
        salida = SalidaAgente.model_validate_json(resultado)
        assert salida.es_phishing is True
        assert salida.resumen == "Custom"


# --- GroqAdapter tests (sin llamada real) ---


class TestGroqAdapter:
    """Tests del adapter Groq (sin llamada a la API real)."""

    def test_groq_sin_api_key_lanza_error(self) -> None:
        """GroqAdapter sin GROQ_API_KEY → ValueError al invocar."""
        from src.level2_agent.agente.groq_adapter import GroqAdapter

        os.environ.pop("GROQ_API_KEY", None)
        adapter = GroqAdapter()
        try:
            adapter.invocar("test")
            pytest.fail("Debería lanzar error sin GROQ_API_KEY")
        except (ValueError, ImportError):
            pass  # ValueError si no hay key, ImportError si langchain_openai no instalado

    def test_groq_modelo_default(self) -> None:
        """GroqAdapter usa el modelo default si no se especifica."""
        from src.level2_agent.agente.groq_adapter import (
            GROQ_MODELO_DEFAULT,
            GroqAdapter,
        )

        os.environ.pop("LLM_MODELO", None)
        adapter = GroqAdapter()
        assert adapter._modelo_nombre == GROQ_MODELO_DEFAULT

    def test_groq_modelo_custom(self) -> None:
        """GroqAdapter acepta modelo custom."""
        from src.level2_agent.agente.groq_adapter import GroqAdapter

        adapter = GroqAdapter(modelo="mixtral-8x7b-32768")
        assert adapter._modelo_nombre == "mixtral-8x7b-32768"


# --- Integración: consultar_agente con factory ---


class TestIntegracionFactory:
    """Tests de integración del agente con la factory."""

    def test_consultar_agente_con_simulado(self) -> None:
        """consultar_agente(modelo=crear_modelo("simulado")) funciona."""
        from src.level2_agent.agente import consultar_agente, crear_modelo
        from src.level2_agent.agente.modelos import EntradaAgente
        from src.level2_agent.models import EmailData
        from src.level3_logic.scoring.modelos import ScoreFinal

        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("VT_API_KEY", None)

        entrada = EntradaAgente(
            email_data=EmailData(subject="Test"),
            score_final=ScoreFinal(
                score_final=50,
                score_clasificador=50.0,
                puntos_banderas=0,
                version_modelo="test",
            ),
        )
        modelo = crear_modelo("simulado")
        # Contador aislado (auditoría): sin él, el tope diario real de
        # MongoDB (llm_contador, agotado a 100/100) retornaba tope_superado.
        from dobles_agente import ContadorDoble

        resultado = consultar_agente(
            entrada, modelo=modelo, contador=ContadorDoble()  # type: ignore[arg-type]
        )
        assert resultado is not None
        assert resultado.salida is not None
