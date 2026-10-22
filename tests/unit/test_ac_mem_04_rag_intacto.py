"""AC-MEM-04: la base de conocimiento vectorial (RAG) conserva sus documentos.

FR-005 — el script de migración solo puede operar sobre `memory-agent`;
`phishguard.docs_phishing` (índice `vector_index`) no recibe ninguna
operación de escritura, ni en modo simulación ni con `--confirmar`.
"""

from __future__ import annotations

from typing import Any

import pytest
import scripts.eliminar_memoria as mod

from dobles_mongo import FakeClienteMongo

URI_FALSA = "mongodb://localhost:27017/por_defecto"

DOCS_RAG = [{"_id": i, "texto": f"control_nist_{i}"} for i in range(7)]


def _cliente_completo() -> FakeClienteMongo:
    """Doble con historial (10 docs) y RAG (7 docs) como en un Atlas real."""
    historial = [{"_id": i} for i in range(10)]
    rag = [dict(d) for d in DOCS_RAG]
    return FakeClienteMongo(
        {"memory-agent": {"memory": historial}, "phishguard": {"docs_phishing": rag}}
    )


@pytest.fixture
def entorno_rag(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    """Entorno aislado: URI ficticia y memory.py dado por INEXISTENTE."""
    monkeypatch.setenv("MONGODB_ATLAS_CLUSTER_URI", URI_FALSA)
    monkeypatch.setattr(mod, "RUTA_MEMORY", tmp_path / "no_existe.py")
    return tmp_path


@pytest.mark.ac("AC-MEM-04")
def test_rag_intacto_tras_el_borrado_confirmado(entorno_rag: Any) -> None:
    """--confirmar: el historial desaparece y el RAG conserva SUS 7 documentos."""
    cliente = _cliente_completo()
    indice_previo = cliente.bases["phishguard"]["docs_phishing"][0].keys()

    codigo = mod.main(["--confirmar"], cliente=cliente)

    assert codigo == 0
    # Historial eliminado (AC-MEM-03):
    assert cliente.bases["memory-agent"] == {}
    # RAG intacto: mismos documentos, mismo contenido, sin cambios:
    assert cliente.bases["phishguard"]["docs_phishing"] == DOCS_RAG
    assert len(cliente.bases["phishguard"]["docs_phishing"]) == 7
    assert set(cliente.bases["phishguard"]["docs_phishing"][0].keys()) == set(indice_previo)


@pytest.mark.ac("AC-MEM-04")
def test_rag_intacto_en_simulacion(entorno_rag: Any) -> None:
    """Modo simulación: tampoco se toca el RAG (no se escribe nada en ninguna base)."""
    cliente = _cliente_completo()

    codigo = mod.main([], cliente=cliente)

    assert codigo == 0
    assert cliente.bases["memory-agent"]["memory"] == [{"_id": i} for i in range(10)]
    assert cliente.bases["phishguard"]["docs_phishing"] == DOCS_RAG


@pytest.mark.ac("AC-MEM-04")
def test_el_rag_no_es_un_objetivo_del_script(entorno_rag: Any) -> None:
    """I1 (contrato): la base del RAG no puede ser destino de ninguna operación."""
    cliente = _cliente_completo()

    codigo = mod.eliminar_historial(cliente, confirmar=True, base="phishguard")

    assert codigo == 1  # guardia: solo memory-agent es objetivo
    assert cliente.bases["phishguard"]["docs_phishing"] == DOCS_RAG
