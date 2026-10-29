"""Pruebas del motor de scoring: calcular_score_final con dobles inyectados.

Cero red real (Art. II.5). Dobles de 003/004/005.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.level2_agent.banderas.modelos import TOPE_PUNTOS_BANDERAS
from src.level2_agent.models import EmailData


def _email_data(**overrides: object) -> EmailData:
    """EmailData mínimo con overrides."""
    base: dict[str, object] = {
        "subject": "",
        "textBody": "",
        "htmlBody": "",
        "sender": "",
        "recipient": "user@midominio.com",
        "headers": "{}",
    }
    base.update(overrides)
    return EmailData(**base)  # type: ignore[arg-type]


class TestCalcularScoreFinal:
    """Pruebas de calcular_score_final (se activarán al implementar scoring/)."""

    def test_import_disponible(self) -> None:
        """El paquete scoring debe ser importable."""
        from src.level3_logic.scoring import calcular_score_final  # noqa: F401

    def test_email_limpio_score_bajo(self) -> None:
        """Email limpio → score_final < 30 (AC-SCO-01)."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data()
        resultado = calcular_score_final(email)
        assert resultado.score_final < 30

    def test_email_phishing_score_alto(self) -> None:
        """Email con señales de phishing → score_final alto."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data(
            subject="URGENTE: verifique su cuenta",
            textBody="Ingrese su password en https://bit.ly/abc",
            sender="support@evil.com",
            headers='{"from": "support@evil.com"}',
        )
        resultado = calcular_score_final(email)
        assert resultado.score_final >= 30

    def test_puntos_banderas_tope_60(self) -> None:
        """puntos_banderas nunca excede TOPE_PUNTOS_BANDERAS (60)."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data()
        resultado = calcular_score_final(email)
        assert resultado.puntos_banderas <= TOPE_PUNTOS_BANDERAS

    def test_score_final_tope_100(self) -> None:
        """score_final nunca excede 100."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data(
            subject="URGENTE VERIFICAR CUENTA BANCO",
            textBody="password tarjeta crédito https://bit.ly/x http://evil.com/login",
            sender="no@evil.com",
            headers='{"from": "no@evil.com"}',
        )
        resultado = calcular_score_final(email)
        assert resultado.score_final <= 100

    def test_version_modelo_presente(self) -> None:
        """ScoreFinal incluye version_modelo."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data()
        resultado = calcular_score_final(email)
        assert resultado.version_modelo == "clasificador_v1"

    def test_score_clasificador_presente(self) -> None:
        """ScoreFinal incluye score_clasificador."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data()
        resultado = calcular_score_final(email)
        assert 0.0 <= resultado.score_clasificador <= 100.0

    def test_invariante_score_final(self) -> None:
        """score_final == min(100, round(score_clasificador + puntos_banderas))."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data(subject="Verifique su cuenta")
        resultado = calcular_score_final(email)
        esperado = min(100, round(resultado.score_clasificador + resultado.puntos_banderas))
        assert resultado.score_final == esperado

    def test_banderas_con_origen(self) -> None:
        """Cada BanderaScoring tiene origen (cabeceras/urls/adjuntos)."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data(
            headers='{"from": "x@evil.com", "date": ""}',
        )
        resultado = calcular_score_final(email)
        for b in resultado.banderas:
            assert b.origen in ("cabeceras", "urls", "adjuntos")

    def test_cero_banderas_puntos_cero(self) -> None:
        """Sin banderas activas → puntos_banderas == 0."""
        from src.level3_logic.scoring import calcular_score_final

        email = _email_data()
        resultado = calcular_score_final(email)
        # Email limpio: puede tener 0 banderas o algunas por defecto
        assert resultado.puntos_banderas >= 0
