"""AC-VT-08: valores límite de la tabla de decisión (3/3/20) y del presupuesto (10)."""

from __future__ import annotations

from typing import Any

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo
from tests.unit.dobles_vt import ClienteDoble, RespuestaDoble, deps_prueba

CONFIG = ConfigVT(api_key="clave-de-prueba", rpm=1000)  # sin esperas de minuto


def _stats(
    malicious: int = 0, suspicious: int = 0, harmless: int = 0, undetected: int = 0
) -> dict[str, Any]:
    """Cuerpo 200 de VirusTotal con los stats dados (M06.4)."""
    return {
        "data": {
            "type": "file",
            "id": "ejemplo",
            "attributes": {
                "last_analysis_stats": {
                    "malicious": malicious,
                    "suspicious": suspicious,
                    "harmless": harmless,
                    "undetected": undetected,
                }
            },
        }
    }


def _consultar_con(body: dict[str, Any]) -> Any:
    """Consulta un hash único (determinista por stats) con el cuerpo 200 dado."""
    sha = (
        f"{body['data']['attributes']['last_analysis_stats']['malicious']:016x}"
        f"{body['data']['attributes']['last_analysis_stats']['suspicious']:016x}"
        f"{body['data']['attributes']['last_analysis_stats']['harmless']:016x}"
        f"{body['data']['attributes']['last_analysis_stats']['undetected']:016x}"
    )
    cliente = ClienteDoble(rutas={("GET", f"/files/{sha}"): [RespuestaDoble(200, body)]})
    return consultar_archivo(sha, config=CONFIG, deps=deps_prueba(cliente))


@pytest.mark.ac("AC-VT-08")
@pytest.mark.parametrize(
    ("malicious", "suspicious", "harmless", "undetected", "esperado"),
    [
        (2, 0, 0, 0, "sospechosa"),  # malicious 1..2 → NO maliciosa (límite inferior)
        (3, 0, 0, 0, "maliciosa"),  # malicious == 3 → maliciosa (límite exacto)
        (0, 3, 0, 0, "sospechosa"),  # suspicious == 3 → sospechosa (límite exacto)
        (0, 2, 0, 0, "desconocida"),  # suspicious 0..2 sin otros apoyos → no sospechosa
        (0, 0, 19, 0, "desconocida"),  # harmless+undetected == 19 → NO limpia
        (0, 0, 0, 20, "limpia"),  # harmless+undetected == 20 → limpia (límite exacto)
    ],
)
def test_tabla_decision_limites(
    malicious: int,
    suspicious: int,
    harmless: int,
    undetected: int,
    esperado: str,
) -> None:
    """Umbrales literales 3/3/20 evaluados por el cliente completo (FR-007, M06.4)."""
    resultado = _consultar_con(_stats(malicious, suspicious, harmless, undetected))
    assert resultado.clasificacion == esperado


@pytest.mark.ac("AC-VT-08")
def test_presupuesto_décima_consulta_pasa_y_undécima_se_omite() -> None:
    """Los 10 primeros viajan; el 11º se omite con VT_PRESUPUESTO_AGOTADO (FR-006)."""
    config = ConfigVT(api_key="clave-de-prueba", rpm=1000, max_por_correo=10)
    cuerpo = _stats(malicious=5)
    rutas = {("GET", f"/files/{i:064x}"): [RespuestaDoble(200, cuerpo)] for i in range(10)}
    cliente = ClienteDoble(rutas=rutas)
    deps = deps_prueba(cliente)
    for i in range(10):
        resultado = consultar_archivo(f"{i:064x}", config=config, deps=deps)
        assert resultado.consultas_externas == 1
    assert sum(1 for p in cliente.peticiones if p.metodo == "GET") == 10

    once = consultar_archivo(f"{10:064x}", config=config, deps=deps)
    assert once.clasificacion == "desconocida"
    assert once.fuente == "sin_llamada"
    assert [b.codigo for b in once.banderas] == ["VT_PRESUPUESTO_AGOTADO"]
    assert sum(1 for p in cliente.peticiones if p.metodo == "GET") == 10
