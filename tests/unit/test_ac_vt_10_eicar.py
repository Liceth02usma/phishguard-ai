"""AC-VT-10: EICAR → maliciosa con respuesta grabada, sin escribir archivos a disco."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo

from dobles_vt import ClienteDoble, RespuestaDoble, cargar_respuesta, deps_prueba
from vector_eicar import EICAR_SHA256, generar_eicar


@pytest.mark.ac("AC-VT-10")
def test_eicar_sha256_en_memoria() -> None:
    """generar_eicar() en memoria da el SHA-256 publicado (SC-003, D9)."""
    assert hashlib.sha256(generar_eicar()).hexdigest() == EICAR_SHA256


@pytest.mark.ac("AC-VT-10")
def test_eicar_maliciosa_con_respuesta_grabada(tmp_path: Path) -> None:
    """El flujo completo con fixture grabada clasifica maliciosa y no toca el disco."""
    cliente = ClienteDoble(
        rutas={
            (
                "GET",
                f"/files/{EICAR_SHA256}",
            ): [RespuestaDoble(200, cargar_respuesta("eicar_maliciosa.json"))]
        }
    )
    antes = set(tmp_path.iterdir())
    resultado = consultar_archivo(
        EICAR_SHA256, config=ConfigVT(api_key="clave-de-prueba"), deps=deps_prueba(cliente)
    )
    assert resultado.clasificacion == "maliciosa"
    assert resultado.stats is not None and resultado.stats.malicious == 60
    assert "VT_ADJ_SOSPECHOSO" in [b.codigo for b in resultado.banderas]
    assert set(tmp_path.iterdir()) == antes  # nada escrito en disco
