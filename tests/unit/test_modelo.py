"""Pruebas del módulo modelo: carga, validación y predicción del clasificador lineal.

AC cubiertos: AC-SCO-03 (version_modelo).
Art. II.5: cero red real. Art. II.6: marcas @pytest.mark.ac.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.level3_logic.genetic_logic import MAPEO_INDICES
from src.level3_logic.modelo import (
    ClasificadorLineal,
    ModeloError,
    cargar_modelo,
    invalidate_cache,
    predecir_probabilidad,
)

RUTA_JSON = Path(__file__).resolve().parent.parent.parent / "data" / "modelo" / "clasificador_v1.json"


@pytest.fixture(autouse=True)
def _limpiar_cache() -> None:
    """Invalida el cache antes y después de cada prueba."""
    invalidate_cache()
    yield
    invalidate_cache()


# --- Carga del JSON real ---


class TestCargaReal:
    """Carga del archivo clasificador_v1.json real."""

    def test_carga_basica(self) -> None:
        """El JSON real carga sin errores."""
        modelo = cargar_modelo(RUTA_JSON)
        assert isinstance(modelo, ClasificadorLineal)

    def test_version(self) -> None:
        """AC-SCO-03: version_modelo == 'clasificador_v1'."""
        modelo = cargar_modelo(RUTA_JSON)
        assert modelo.version == "clasificador_v1"

    def test_intercepto_es_float(self) -> None:
        modelo = cargar_modelo(RUTA_JSON)
        assert isinstance(modelo.intercepto, float)

    def test_coeficientes_32_entradas(self) -> None:
        """Los coeficientes tienen exactamente 32 entradas."""
        modelo = cargar_modelo(RUTA_JSON)
        assert len(modelo.coeficientes) == 32

    def test_coeficientes_claves_mapeo_indices(self) -> None:
        """Las claves de coeficientes coinciden exactamente con MAPEO_INDICES."""
        modelo = cargar_modelo(RUTA_JSON)
        assert set(modelo.coeficientes.keys()) == set(MAPEO_INDICES)

    def test_fecha_formato_iso(self) -> None:
        modelo = cargar_modelo(RUTA_JSON)
        partes = modelo.fecha.split("-")
        assert len(partes) == 3
        assert all(p.isdigit() for p in partes)

    def test_metricas_entrenamiento(self) -> None:
        modelo = cargar_modelo(RUTA_JSON)
        m = modelo.metricas_entrenamiento
        assert 0.0 <= m.accuracy <= 1.0
        assert 0.0 <= m.recall <= 1.0
        assert 0.0 <= m.f1 <= 1.0


# --- Cache de proceso ---


class TestCache:
    """El cache evita releer disco en la segunda llamada."""

    def test_cache_mismo_objeto(self) -> None:
        m1 = cargar_modelo(RUTA_JSON)
        m2 = cargar_modelo(RUTA_JSON)
        assert m1 is m2

    def test_cache_ruta_distinta_recarga(self, tmp_path: Path) -> None:
        """Si la ruta cambia, se recarga (no usa cache de ruta anterior)."""
        m1 = cargar_modelo(RUTA_JSON)
        # Crear un segundo JSON válido
        datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
        datos["version"] = "clasificador_v2"
        otro = tmp_path / "clasificador_v2.json"
        otro.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        m2 = cargar_modelo(otro)
        assert m2.version == "clasificador_v2"


# --- Errores ---


class TestErrores:
    """Art. III.9: fallo ruidoso."""

    def test_archivo_faltante(self, tmp_path: Path) -> None:
        ruta = tmp_path / "no_existe.json"
        with pytest.raises(ModeloError, match="no encontrado"):
            cargar_modelo(ruta)

    def test_json_ilegible(self, tmp_path: Path) -> None:
        ruta = tmp_path / "mal.json"
        ruta.write_text("{invalido", encoding="utf-8")
        with pytest.raises(ModeloError, match="JSON inválido"):
            cargar_modelo(ruta)

    def test_schema_invalido_faltan_campos(self, tmp_path: Path) -> None:
        ruta = tmp_path / "incompleto.json"
        ruta.write_text('{"version": "x"}', encoding="utf-8")
        with pytest.raises(ModeloError, match="Schema inválido"):
            cargar_modelo(ruta)

    def test_coeficientes_faltantes(self, tmp_path: Path) -> None:
        """Claves de coeficientes faltantes ⇒ ModeloError."""
        datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
        # Quitar una clave
        primera = next(iter(datos["coeficientes"]))
        del datos["coeficientes"][primera]
        ruta = tmp_path / "faltan.json"
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ModeloError, match="faltantes"):
            cargar_modelo(ruta)

    def test_coeficientes_sobrantes(self, tmp_path: Path) -> None:
        """Claves de coeficientes sobrantes ⇒ ModeloError."""
        datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
        datos["coeficientes"]["gen_inventado"] = 0.5
        ruta = tmp_path / "sobran.json"
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ModeloError, match="sobrantes"):
            cargar_modelo(ruta)


# --- Predicción ---


class TestPredecirProbabilidad:
    """predecir_probabilidad: producto punto + sigmoide."""

    def test_cero_genes_score_bajo(self) -> None:
        """AC-SCO-01: 0 genes → score < 30."""
        modelo = cargar_modelo(RUTA_JSON)
        prob = predecir_probabilidad(modelo, [0] * 32)
        score = prob * 100.0
        assert score < 30.0

    def test_todos_genes_activos(self) -> None:
        modelo = cargar_modelo(RUTA_JSON)
        prob = predecir_probabilidad(modelo, [1] * 32)
        assert 0.0 <= prob <= 1.0

    def test_rango_cero_a_uno(self) -> None:
        """La probabilidad siempre está en [0, 1]."""
        modelo = cargar_modelo(RUTA_JSON)
        for genes in ([0] * 32, [1] * 32, [1, 0] * 16):
            prob = predecir_probabilidad(modelo, genes)
            assert 0.0 <= prob <= 1.0

    def test_monotonia_agregar_gen_positivo(self) -> None:
        """Si un gen con coeficiente positivo pasa de 0 a 1, la probabilidad sube."""
        modelo = cargar_modelo(RUTA_JSON)
        genes_base = [0] * 32
        prob_base = predecir_probabilidad(modelo, genes_base)
        # Buscar un gen con coeficiente positivo
        for i, nombre in enumerate(MAPEO_INDICES):
            if modelo.coeficientes[nombre] > 0:
                genes_mod = list(genes_base)
                genes_mod[i] = 1
                prob_mod = predecir_probabilidad(modelo, genes_mod)
                assert prob_mod > prob_base
                break
