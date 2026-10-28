"""AC-VT-04: 429/500/502/503 → 3 reintentos con 1/2/4 s + jitter; Retry-After; 404/400 sin."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo
from tests.unit.dobles_vt import (
    ClienteDoble,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
CONFIG = ConfigVT(api_key="clave-de-prueba")
RUTA = f"/files/{SHA}"


@pytest.mark.ac("AC-VT-04")
def test_429_con_retry_after_respeta_el_encabezado() -> None:
    """429 con Retry-After: 7 s → una espera de 7.0 s y luego 200 (FR-003)."""
    cuerpo = cargar_respuesta("archivo_maliciosa.json")
    cliente = ClienteDoble(
        rutas={
            (
                "GET",
                RUTA,
            ): [
                RespuestaDoble(429, {}, {"retry-after": "7"}),
                RespuestaDoble(200, cuerpo),
            ]
        }
    )
    deps = deps_prueba(cliente)
    resultado = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert resultado.clasificacion == "maliciosa"
    assert deps.dormir is not None
    assert deps.dormir.esperas == [7.0]
    assert cliente.contar("GET", RUTA) == 2


@pytest.mark.ac("AC-VT-04")
def test_429_persistente_reintenta_3_veces_1_2_4() -> None:
    """429 sin Retry-After → espera exponencial 1/2/4 s y 4 peticiones en total (FR-003)."""
    cliente = ClienteDoble(
        rutas={("GET", RUTA): [RespuestaDoble(429, {})] * 4}
    )
    deps = deps_prueba(cliente)
    resultado = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert resultado.clasificacion == "desconocida"
    assert deps.dormir is not None
    assert deps.dormir.esperas == [1.0, 2.0, 4.0]
    assert cliente.contar("GET", RUTA) == 4


@pytest.mark.ac("AC-VT-04")
@pytest.mark.parametrize("estado", [500, 502, 503])
def test_5xx_persistente_reintenta_3_veces(estado: int) -> None:
    """500/502/503 → 3 reintentos con la misma espera exponencial (FR-003)."""
    cliente = ClienteDoble(rutas={("GET", RUTA): [RespuestaDoble(estado, {})] * 4})
    deps = deps_prueba(cliente)
    resultado = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert resultado.clasificacion == "desconocida"
    assert deps.dormir is not None
    assert deps.dormir.esperas == [1.0, 2.0, 4.0]
    assert cliente.contar("GET", RUTA) == 4
    assert "VT_DESCONOCIDO" in [b.codigo for b in resultado.banderas]


@pytest.mark.ac("AC-VT-04")
@pytest.mark.parametrize("estado", [404, 400])
def test_404_y_400_sin_reintentos(estado: int) -> None:
    """404 y 400 son terminales: exactamente una petición y cero esperas (FR-003)."""
    cuerpo = cargar_respuesta("no_encontrado.json") if estado == 404 else {}
    cliente = ClienteDoble(rutas={("GET", RUTA): [RespuestaDoble(estado, cuerpo)]})
    deps = deps_prueba(cliente)
    consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert cliente.contar("GET", RUTA) == 1
    assert deps.dormir is not None
    assert deps.dormir.esperas == []


@pytest.mark.ac("AC-VT-04")
def test_error_de_transport_no_reintenta() -> None:
    """Un error de transporte es fallo directo (D6): 1 intento, sin esperas."""
    cliente = ClienteDoble()  # sin ruta registrada → el doble lanza
    deps = deps_prueba(cliente)
    resultado = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert resultado.clasificacion == "desconocida"
    assert deps.dormir is not None
    assert deps.dormir.esperas == []
    assert cliente.contar("GET", RUTA) == 1
