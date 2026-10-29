"""Pruebas adicionales de cobertura: scoring/modelos, scoring/configuracion."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.level3_logic.scoring.modelos import (
    BanderaScoring,
    GenImplicado,
    ModeloError,
    ScoreFinal,
    ScoringError,
)
from src.level3_logic.scoring.configuracion import ConfigScoring, PROVEEDORES_CONFIANZA_POR_DEFECTO
from src.level2_agent.banderas.modelos import TOPE_PUNTOS_BANDERAS


class TestScoringError:
    """Jerarquía de excepciones."""

    def test_modelo_error_hereda_scoring_error(self) -> None:
        assert issubclass(ModeloError, ScoringError)

    def test_scoring_error_es_exception(self) -> None:
        assert issubclass(ScoringError, Exception)


class TestBanderaScoring:
    """Modelo BanderaScoring."""

    def test_origen_valido(self) -> None:
        b = BanderaScoring(origen="cabeceras", codigo="TEST", puntos=5)
        assert b.origen == "cabeceras"

    def test_orden(self) -> None:
        b1 = BanderaScoring(origen="cabeceras", codigo="A", puntos=1)
        b2 = BanderaScoring(origen="urls", codigo="B", puntos=2)
        assert b1 < b2


class TestScoreFinal:
    """Validaciones de ScoreFinal."""

    def test_invariante_rota(self) -> None:
        with pytest.raises(ValueError, match="Invariante rota"):
            ScoreFinal(
                score_final=50,
                score_clasificador=30.0,
                puntos_banderas=10,
                version_modelo="test",
            )

    def test_puntos_banderas_excede_tope(self) -> None:
        with pytest.raises(ValueError, match="puntos_banderas"):
            ScoreFinal(
                score_final=100,
                score_clasificador=50.0,
                puntos_banderas=TOPE_PUNTOS_BANDERAS + 1,
                version_modelo="test",
            )

    def test_score_final_valido(self) -> None:
        sf = ScoreFinal(
            score_final=82,
            score_clasificador=41.75,
            puntos_banderas=40,
            version_modelo="clasificador_v1",
        )
        assert sf.score_final == 82

    def test_score_final_tope_100(self) -> None:
        sf = ScoreFinal(
            score_final=100,
            score_clasificador=80.0,
            puntos_banderas=60,
            version_modelo="test",
        )
        assert sf.score_final == 100


class TestConfigScoring:
    """Configuración desde entorno."""

    def test_default(self) -> None:
        config = ConfigScoring()
        assert config.dominios_propios == ()
        assert config.proveedores_confianza == PROVEEDORES_CONFIANZA_POR_DEFECTO

    def test_desde_entorno_vacio(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigScoring.desde_entorno()
            assert config.dominios_propios == ()

    def test_desde_entorno_con_vars(self) -> None:
        env = {
            "DOMINIOS_PROPIOS": "empresa.com,corp.com",
            "DOMINIOS_PROVEEDORES_CONFIANZA": "google.com",
        }
        with patch.dict(os.environ, env, clear=False):
            config = ConfigScoring.desde_entorno()
            assert "empresa.com" in config.dominios_propios
            assert "corp.com" in config.dominios_propios
            assert "google.com" in config.proveedores_confianza

    def test_desde_entorno_ruta_modelo(self) -> None:
        with patch.dict(os.environ, {"RUTA_MODELO": "/tmp/model.json"}, clear=False):
            config = ConfigScoring.desde_entorno()
            assert config.ruta_modelo == Path("/tmp/model.json")
