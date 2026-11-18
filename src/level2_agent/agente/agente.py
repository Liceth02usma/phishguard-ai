"""Orquestador del agente de IA sin estado (spec 009, M07).

consultar_agente(entrada) -> ResultadoAgente:
1. Verifica tope diario; si superado, retorna sin llamar modelo.
2. Construye prompt con evidencia estructurada y delimitadores.
3. Invoca modelo (temperatura 0, herramienta busqueda_vectorial).
4. Valida salida con esquema SalidaAgente; si falla, 1 reintento.
5. Retorna ResultadoAgente con confirmacion_agente para el motor de decisión.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.level2_agent.agente.contador import ContadorLLM
from src.level2_agent.agente.modelos import (
    MAX_REINTENTOS,
    EntradaAgente,
    ModeloLLM,
    ResultadoAgente,
    SalidaAgente,
)
from src.level2_agent.agente.prompt import construir_prompt
from src.level2_agent.agente.validador import validar_salida
from src.level2_agent.tools import create_retriever


def _construir_herramientas() -> list[Any]:
    """Construye la lista de herramientas del agente (FR-002, AC-AGT-01).

    Solo busqueda_vectorial (RAG de solo lectura).
    Se retira check_ip_reputation y jira_integration.
    """
    herramientas: list[object] = []
    try:
        retriever = create_retriever()  # type: ignore[no-untyped-call]
        if retriever is not None:
            from langchain_core.tools import tool

            @tool("busqueda_vectorial")
            def busqueda_vectorial(query: str) -> str:
                """Busca en la base de conocimiento vectorial (NIST/OWASP/MITRE)."""
                docs = retriever.invoke(query)
                return "\n".join(d.page_content for d in docs)

            herramientas.append(busqueda_vectorial)
    except Exception:
        pass  # RAG no disponible — agente funciona sin herramienta
    return herramientas


def _obtener_modelo(modelo: ModeloLLM | None = None) -> ModeloLLM:
    """Obtiene el modelo LLM (Adapter, FR-008).

    Si no se proporciona uno, usa la factory (Strategy) que lee
    LLM_PROVEEDOR del entorno (default: "gemini").
    """
    if modelo is not None:
        return modelo

    from src.level2_agent.agente.factory import crear_modelo

    return crear_modelo()  # type: ignore[return-value]


def consultar_agente(
    entrada: EntradaAgente,
    *,
    modelo: ModeloLLM | None = None,
    contador: ContadorLLM | None = None,
    ahora: date | None = None,
) -> ResultadoAgente:
    """Agente de IA sin estado (M07).

    1. Verifica tope diario; si superado, retorna revision_manual.
    2. Construye prompt con evidencia y delimitadores.
    3. Invoca modelo con busqueda_vectorial.
    4. Valida salida; si falla, 1 reintento.
    5. Retorna ResultadoAgente.
    """
    # Paso 1: verificar tope diario (FR-007, AC-AGT-05)
    if contador is None:
        contador = ContadorLLM(ahora=ahora)

    if not contador.disponible():
        return ResultadoAgente(
            salida=None,
            confirmacion_agente=None,
            reintentos=0,
            llamadas_modelo=0,
            razon="tope_superado",
        )

    # Paso 2: construir prompt
    prompt = construir_prompt(entrada)

    # Paso 3: obtener modelo y herramientas
    llm = _obtener_modelo(modelo)
    herramientas = _construir_herramientas()

    # Paso 4: invocar modelo con reintento (FR-004, AC-AGT-03)
    llamadas = 0
    salida_valida: SalidaAgente | None = None

    for _intento in range(MAX_REINTENTOS + 1):
        llamadas += 1
        contador.incrementar()

        try:
            raw = llm.invocar(prompt, herramientas=herramientas)
            salida_valida = validar_salida(raw)
        except Exception:
            salida_valida = None

        if salida_valida is not None:
            break  # Éxito

    # Paso 5: ensamblar resultado
    if salida_valida is not None:
        return ResultadoAgente(
            salida=salida_valida,
            confirmacion_agente=salida_valida.es_phishing,
            reintentos=_intento if salida_valida is not None else llamadas,
            llamadas_modelo=llamadas,
            razon="exito",
        )
    else:
        return ResultadoAgente(
            salida=None,
            confirmacion_agente=None,
            reintentos=llamadas,
            llamadas_modelo=llamadas,
            razon="validacion_fallida",
        )
