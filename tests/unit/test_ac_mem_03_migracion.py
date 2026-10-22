"""AC-MEM-03: el script de migración elimina las colecciones de historial.

Tabla de decisión del contrato (contracts/eliminar-memoria-cli.md, filas 1–6)
más valores límite de TAMANO_LOTE (Art. II.2 — análisis de valores límite y
tabla de decisión) contra el doble de cliente Mongo. Sin red real (Art. II.5).
"""

from __future__ import annotations

from typing import Any

import pytest
import scripts.eliminar_memoria as mod

from dobles_mongo import FakeClienteMongo

URI_FALSA = "mongodb://localhost:27017/por_defecto"


def _cliente_con_documentos(n_docs: int) -> FakeClienteMongo:
    """Cliente doble con una colección memory de n_docs documentos."""
    return FakeClienteMongo({"memory-agent": {"memory": [{"_id": i} for i in range(n_docs)]}})


@pytest.fixture
def entorno_migracion(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    """Entorno aislado: URI ficticia y memory.py dado por INEXISTENTE por defecto."""
    monkeypatch.setenv("MONGODB_ATLAS_CLUSTER_URI", URI_FALSA)
    monkeypatch.setattr(mod, "RUTA_MEMORY", tmp_path / "aun_no_existe.py")
    return tmp_path


# --- Valores límite de TAMANO_LOTE (número exacto de lotes) ---


@pytest.mark.ac("AC-MEM-03")
@pytest.mark.parametrize(
    ("n_docs", "lotes_esperados"),
    [
        (0, 0),
        (1, 1),
        (mod.TAMANO_LOTE, 1),
        (mod.TAMANO_LOTE + 1, 2),
        (mod.TAMANO_LOTE * 3 + 7, 4),
    ],
)
def test_eliminar_por_lotes_valores_limite(
    n_docs: int, lotes_esperados: int
) -> None:
    """El borrado por lotes vacía la colección con el número exacto de lotes."""
    cliente = _cliente_con_documentos(n_docs)
    coleccion = cliente.get_database(mod.BASE_HISTORIAL).get_collection(mod.COLECCION_HISTORIAL)

    total, lotes = mod.eliminar_por_lotes(coleccion, mod.TAMANO_LOTE)

    assert total == n_docs
    assert lotes == lotes_esperados
    assert coleccion.count_documents({}) == 0


# --- Tabla de decisión (filas 1–6 del contrato) ---


@pytest.mark.ac("AC-MEM-03")
def test_fila_1_simulacion_no_borra_nada(entorno_migracion: Any, capsys: Any) -> None:
    """Sin --confirmar: informa el plan (N docs, lotes) y NO escribe nada."""
    cliente = _cliente_con_documentos(7)

    codigo = mod.main([], cliente=cliente)

    assert codigo == 0
    assert cliente.bases["memory-agent"]["memory"] == [{"_id": i} for i in range(7)]
    salida = capsys.readouterr().out
    assert "[SIMULACIÓN]" in salida
    assert "7 documentos" in salida
    assert "1 lote(s)" in salida


@pytest.mark.ac("AC-MEM-03")
def test_fila_2_simulacion_sin_colecciones_es_exit_cero(
    entorno_migracion: Any, capsys: Any
) -> None:
    """Base sin colecciones: sin error, exit 0 (edge case de spec)."""
    cliente = FakeClienteMongo({})

    codigo = mod.main([], cliente=cliente)

    assert codigo == 0
    assert "nada que eliminar" in capsys.readouterr().out


@pytest.mark.ac("AC-MEM-03")
def test_fila_3_confirmado_elimina_las_colecciones(entorno_migracion: Any, capsys: Any) -> None:
    """Con --confirmar: vacía por lotes, elimina la colección y sale con 0."""
    cliente = _cliente_con_documentos(mod.TAMANO_LOTE + 5)

    codigo = mod.main(["--confirmar"], cliente=cliente)

    assert codigo == 0
    assert "memory" not in cliente.bases["memory-agent"]
    salida = capsys.readouterr().out
    assert "[ELIMINADO]" in salida
    assert "2 lote(s)" in salida


@pytest.mark.ac("AC-MEM-03")
def test_fila_4_confirmado_sin_colecciones_es_exit_cero(entorno_migracion: Any) -> None:
    """--confirmar sobre base vacía/inexistente: sin error, exit 0 (edge case)."""
    cliente = FakeClienteMongo({"otra-base": {"algo": [{"_id": 1}]}})

    codigo = mod.main(["--confirmar"], cliente=cliente)

    assert codigo == 0
    assert cliente.bases["otra-base"] == {"algo": [{"_id": 1}]}  # intocado


@pytest.mark.ac("AC-MEM-03")
def test_fila_5_aborta_si_memory_py_aun_existe(
    entorno_migracion: Any, capsys: Any
) -> None:
    """Validación previa: si el módulo de memoria existe, exit 1 con cero escrituras."""
    (entorno_migracion / "aun_no_existe.py").write_text("# aún existe\n", encoding="utf-8")
    cliente = _cliente_con_documentos(3)

    codigo = mod.main(["--confirmar"], cliente=cliente)

    assert codigo == 1
    assert len(cliente.bases["memory-agent"]["memory"]) == 3  # nada borrado
    assert "ERROR" in capsys.readouterr().err


@pytest.mark.ac("AC-MEM-03")
def test_fila_6_aborta_si_la_base_no_es_el_objetivo(
    entorno_migracion: Any, capsys: Any
) -> None:
    """Guardia: la única base aceptada es memory-agent; nada se escribe en otra."""
    cliente = FakeClienteMongo({"phishguard": {"docs_phishing": [{"_id": i} for i in range(4)]}})

    codigo = mod.eliminar_historial(cliente, confirmar=True, base="phishguard")

    assert codigo == 1
    assert len(cliente.bases["phishguard"]["docs_phishing"]) == 4
    assert "ERROR" in capsys.readouterr().err


@pytest.mark.ac("AC-MEM-03")
def test_aborta_sin_variable_de_entorno(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    """Sin MONGODB_ATLAS_CLUSTER_URI: exit 1 con mensaje (validación V3)."""
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)

    codigo = mod.main([])

    assert codigo == 1
    assert "MONGODB_ATLAS_CLUSTER_URI" in capsys.readouterr().err


@pytest.mark.ac("AC-MEM-03")
def test_error_de_conexion_es_exit_uno_con_mensaje(
    entorno_migracion: Any, capsys: Any
) -> None:
    """Un fallo al consultar MongoDB se informa (Art. III.9) sin excepción descontrolada."""

    class _ClienteRoto:
        def get_database(self, nombre: str) -> Any:
            raise RuntimeError("sin conexión a MongoDB")

    codigo = mod.main(["--confirmar"], cliente=_ClienteRoto())

    assert codigo == 1
    assert "sin conexión" in capsys.readouterr().err
