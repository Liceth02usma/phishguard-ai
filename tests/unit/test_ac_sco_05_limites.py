"""AC-SCO-05: límites — tope 60 puntos_banderas y tope 100 score_final.

Tabla de valores límite: 59/60/61 puntos y 99/100/101 score previo.
"""

from __future__ import annotations

import pytest

from src.level2_agent.banderas.modelos import TOPE_PUNTOS_BANDERAS


def _score_final(score_clasificador: float, puntos_banderas: int) -> int:
    return min(100, round(score_clasificador + min(TOPE_PUNTOS_BANDERAS, puntos_banderas)))


@pytest.mark.ac("AC-SCO-05")
class TestTopePuntosBanderas:
    """Tope de puntos_banderas = 60 (TOPE_PUNTOS_BANDERAS)."""

    def test_59_puntos_sin_tope(self) -> None:
        """59 puntos → no se trunca."""
        assert _score_final(0.0, 59) == 59

    def test_60_puntos_en_el_tope(self) -> None:
        """60 puntos → exactamente en el tope."""
        assert _score_final(0.0, 60) == 60

    def test_61_puntos_truncado(self) -> None:
        """61 puntos → se trunca a 60."""
        assert _score_final(0.0, 61) == 60

    def test_100_puntos_truncado(self) -> None:
        """100 puntos → se trunca a 60."""
        assert _score_final(0.0, 100) == 60


@pytest.mark.ac("AC-SCO-05")
class TestTopeScoreFinal:
    """Tope de score_final = 100."""

    def test_99_no_trunca(self) -> None:
        """score_clasificador=99 + 0 banderas → 99."""
        assert _score_final(99.0, 0) == 99

    def test_100_exacto(self) -> None:
        """score_clasificador=100 + 0 banderas → 100."""
        assert _score_final(100.0, 0) == 100

    def test_101_truncado(self) -> None:
        """score_clasificador=101 + 0 banderas → 100 (tope)."""
        assert _score_final(101.0, 0) == 100

    def test_combinacion_tope_doble(self) -> None:
        """score_clasificador=50 + 60 banderas = 110 → 100."""
        assert _score_final(50.0, 60) == 100

    def test_score_41_mas_60(self) -> None:
        """score_clasificador=41.75 + 40 banderas = 82 (sin tope)."""
        assert _score_final(41.75, 40) == 82
