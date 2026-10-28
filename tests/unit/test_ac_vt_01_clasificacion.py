"""AC-VT-01: hash con malicious=5 → maliciosa; 404 → desconocida, nunca limpia (G1, G12)."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo

from dobles_vt import ClienteDoble, RespuestaDoble, cargar_respuesta, deps_prueba

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


def _config() -> ConfigVT:
    """Configuración de prueba con clave presente (flujo normal)."""
    return ConfigVT(api_key="clave-de-prueba")


@pytest.mark.ac("AC-VT-01")
def test_hash_malicious_5_es_maliciosa() -> None:
    """GET /files/{sha} con malicious=5 clasifica maliciosa con flag de catálogo 5.3."""
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/files/{SHA}"): [
                RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
            ]
        }
    )
    resultado = consultar_archivo(SHA, config=_config(), deps=deps_prueba(cliente))
    assert resultado.clasificacion == "maliciosa"
    assert resultado.fuente == "red"
    assert resultado.consultas_externas == 1
    assert resultado.stats is not None and resultado.stats.malicious == 5
    adj = next(b for b in resultado.banderas if b.codigo == "VT_ADJ_SOSPECHOSO")
    assert adj.severidad == "alta" and adj.puntos == 25


@pytest.mark.ac("AC-VT-01")
def test_hash_404_desconocida_nunca_limpia() -> None:
    """404 → desconocida + VT_DESCONOCIDO; jamás se reporta como limpia (FR-001)."""
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/files/{SHA}"): [
                RespuestaDoble(404, cargar_respuesta("no_encontrado.json"))
            ]
        }
    )
    resultado = consultar_archivo(SHA, config=_config(), deps=deps_prueba(cliente))
    assert resultado.clasificacion == "desconocida"
    # El 404 jamás se reporta como «limpia»: el veredicto queda en desconocida (FR-001).
    assert resultado.stats is None
    assert [b.codigo for b in resultado.banderas] == ["VT_DESCONOCIDO"]
    assert cliente.contar("GET", f"/files/{SHA}") == 1


@pytest.mark.ac("AC-VT-01")
def test_hash_malformado_sin_llamada_no_lanza() -> None:
    """G12: hash que no es hex-64 → desconocida sin excepción y sin petición (III.9)."""
    cliente = ClienteDoble()
    resultado = consultar_archivo("no-es-hex64", config=_config(), deps=deps_prueba(cliente))
    assert resultado.clasificacion == "desconocida"
    assert resultado.fuente == "sin_llamada"
    assert resultado.consultas_externas == 0
    assert [b.codigo for b in resultado.banderas] == ["VT_DESCONOCIDO"]
    assert cliente.peticiones == []
