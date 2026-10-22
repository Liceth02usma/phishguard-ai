"""AC-MEM-01: ninguna ruta de código importa o escribe historial de chat.

Comprobación estática sobre el repositorio (Art. II.2 — partición de
equivalencia: código con restos de memoria vs código limpio). También cubre
FR-004 (README/configuración sin textos de memoria).

NO escanea ``docs/`` (documentos fuente históricos, research D10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

PROHIBIDOS_EN_CODIGO = (
    "get_chat_history",
    "MongoDBChatMessageHistory",
    "chat_history",
    "session_id",
    "MEMORY_TOOL",
    "MEMORY_DATABASE",
    "MEMORY_COLLECTION",
    "add_user_message",
    "add_ai_message",
    "langchain_mongodb.chat_message_histories",
)

TEXTOS_PROHIBIDOS_EN_DOCS = (
    "memory.py",
    "memoria conversacional",
    "Chat history",
    "memory-agent",
    "MEMORY_TOOL",
)

DOCUMENTOS_REVISADOS = ("README.md", "AGENTS.md", ".env.example")


@pytest.mark.ac("AC-MEM-01")
def test_el_modulo_de_memoria_no_existe() -> None:
    """FR-001: src/level2_agent/memory.py ha sido eliminado."""
    ruta = RAIZ / "src" / "level2_agent" / "memory.py"
    assert not ruta.exists(), f"{ruta} no debe existir (FR-001)"


@pytest.mark.ac("AC-MEM-01")
def test_el_codigo_fuente_no_tiene_rastros_de_memoria() -> None:
    """FR-001: ningún .py de src/ importa o escribe historial de chat."""
    infracciones: list[str] = []
    for ruta in sorted((RAIZ / "src").rglob("*.py")):
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
        for patron in PROHIBIDOS_EN_CODIGO:
            if patron in contenido:
                infracciones.append(f"{ruta.relative_to(RAIZ)}: '{patron}'")
    assert not infracciones, (
        "Restos de memoria conversacional en el código:\n" + "\n".join(infracciones)
    )


@pytest.mark.ac("AC-MEM-01")
@pytest.mark.parametrize("documento", DOCUMENTOS_REVISADOS)
def test_documentacion_y_configuracion_sin_textos_de_memoria(documento: str) -> None:
    """FR-004: README, guía de agentes y .env.example sin texto ni variable de memoria."""
    ruta = RAIZ / documento
    assert ruta.exists(), f"{documento} debe existir para poder revisarlo"
    contenido = ruta.read_text(encoding="utf-8", errors="replace").lower()
    for texto in TEXTOS_PROHIBIDOS_EN_DOCS:
        assert texto.lower() not in contenido, (
            f"{documento} aún menciona '{texto}' (FR-004)"
        )
