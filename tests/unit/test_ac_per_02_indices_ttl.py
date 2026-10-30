"""AC-PER-02: los índices TTL existen con las retenciones indicadas (FR-003)."""

from __future__ import annotations

from src.level2_agent.persistencia.repositorio import RepositorioDoble
from src.level2_agent.persistencia.modelos import (
    RETENCION_ANALISIS_DIAS,
    RETENCION_FALLIDOS_DIAS,
)


def test_indices_tlb_en_doble() -> None:
    """RepositorioDoble reporta los índices esperados."""
    repo = RepositorioDoble()
    indices = repo.indices_existentes()
    assert "ttl_analisis" in indices
    assert "idx_fecha" in indices
    assert "idx_veredicto" in indices
    assert "idx_message_id" in indices


def test_constantes_retencion() -> None:
    """Las constantes de retención tienen los valores de FR-001."""
    assert RETENCION_ANALISIS_DIAS == 90
    assert RETENCION_FALLIDOS_DIAS == 30
