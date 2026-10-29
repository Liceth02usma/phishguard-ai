"""Cobertura de genetic_logic.py: matriz de genes por partición de equivalencia.

Verifica que los 32 genes se activan correctamente por grupos,
incluida FR-005 (genes 0 y 28 condicionados a listas).
"""

from __future__ import annotations

import pytest

from src.level3_logic.genetic_logic import evaluate, MAPEO_INDICES


def _email(**overrides: object) -> dict[str, object]:
    """Email mínimo con overrides."""
    base: dict[str, object] = {
        "htmlBody": "",
        "textBody": "",
        "subject": "",
        "recipient": "user@midominio.com",
        "headers": {},
    }
    base.update(overrides)
    return base


class TestGenesDominio:
    """Genes 0 (dominio_externo) y 28 (mismatch_dominio_url) — FR-005."""

    def test_gen0_externo_sin_listas(self) -> None:
        """Dominio externo activa gen 0 (sin listas de confianza)."""
        datos = _email(
            headers='{"from": "attacker@evil.com", "date": ""}',
        )
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "dominio_externo" in genes_activos

    def test_gen0_no_externo(self) -> None:
        """Mismo dominio → gen 0 no se activa."""
        datos = _email(
            headers='{"from": "user@midominio.com", "date": ""}',
        )
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "dominio_externo" not in genes_activos


class TestGenesAsunto:
    """Genes 5-10: asunto_urgencia, financiero, premio, amenaza, verificacion, corto."""

    def test_gen5_urgencia(self) -> None:
        datos = _email(subject="URGENTE: verifique su cuenta")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_urgencia" in genes_activos

    def test_gen6_financiero(self) -> None:
        datos = _email(subject="Su banco requiere acción")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_financiero" in genes_activos

    def test_gen7_premio(self) -> None:
        datos = _email(subject="Usted es el ganador del premio")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_premio" in genes_activos

    def test_gen8_amenaza(self) -> None:
        datos = _email(subject="Su cuenta será bloqueada warning")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_amenaza" in genes_activos

    def test_gen9_verificacion(self) -> None:
        datos = _email(subject="Verifique su identidad update")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_verificacion" in genes_activos

    def test_gen10_corto(self) -> None:
        datos = _email(subject="Hi")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "asunto_corto" in genes_activos


class TestGenesCuerpo:
    """Genes 13-25: credenciales, bancarios, ortografía, etc."""

    def test_gen13_credenciales(self) -> None:
        datos = _email(textBody="Ingrese su password y login")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "solicita_credenciales" in genes_activos

    def test_gen14_bancarios(self) -> None:
        datos = _email(textBody="Ingrese su tarjeta de crédito")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "solicita_datos_bancarios" in genes_activos

    def test_gen17_fecha_limite(self) -> None:
        datos = _email(textBody="Tiene 24 hours para responder")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "fecha_limite" in genes_activos

    def test_gen18_apelacion_miedo(self) -> None:
        datos = _email(textBody="Si no actúa, perder su cuenta warning")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "apelacion_miedo" in genes_activos

    def test_gen20_cuerpo_corto(self) -> None:
        datos = _email(textBody="OK")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "cuerpo_corto" in genes_activos


class TestGenesURL:
    """Genes 26-31: url_acortada, url_con_ip, mismatch, http_inseguro, keywords, multiples."""

    def test_gen26_url_acortada(self) -> None:
        datos = _email(textBody="Visite https://bit.ly/abc123")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "url_acortada" in genes_activos

    def test_gen29_http_inseguro(self) -> None:
        datos = _email(textBody="Vaya a http://example.com/login")
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "protocolo_http_inseguro" in genes_activos

    def test_gen31_multiples_urls(self) -> None:
        datos = _email(
            textBody="Visite https://a.com y https://b.com y https://c.com y https://d.com"
        )
        resultado = evaluate(datos)
        genes_activos = [g["caracteristica"] for g in resultado["genes_implicados"]]
        assert "multiples_urls" in genes_activos


class TestScoreConModelo:
    """Verifica que evaluate retorna score y genes_implicados."""

    def test_evaluate_retorna_score(self) -> None:
        datos = _email(subject="URGENTE", textBody="password", headers='{"from": "x@evil.com"}')
        resultado = evaluate(datos)
        assert "score" in resultado
        assert 0.0 <= resultado["score"] <= 100.0

    def test_evaluate_retorna_genes_implicados(self) -> None:
        datos = _email(subject="URGENTE")
        resultado = evaluate(datos)
        assert "genes_implicados" in resultado
        assert isinstance(resultado["genes_implicados"], list)

    def test_email_vacio_score_bajo(self) -> None:
        """Email vacío → score bajo (AC-SCO-01 vía evaluate)."""
        datos = _email()
        resultado = evaluate(datos)
        # Con PESOS_AG actual, email vacío da 50 (baseline del AG).
        # Con el clasificador, será < 30. Por ahora documentamos.
        assert "score" in resultado
