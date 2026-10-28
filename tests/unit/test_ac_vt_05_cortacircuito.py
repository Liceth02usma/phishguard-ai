"""AC-VT-05: 5 fallos → abierto 60 s con VT_NO_DISPONIBLE; sin llamada; reset por éxito."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, DependenciasVT, consultar_archivo
from src.level2_agent.virustotal.cache import CacheMemoria
from tests.unit.dobles_vt import (
    ClienteDoble,
    RelojFalso,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
CONFIG = ConfigVT(api_key="clave-de-prueba")
RUTA = f"/files/{SHA}"


def _fallar_cinco(deps: DependenciasVT) -> None:
    """Cinco consultas cuyo transporte lanza (petición no registrada = fallo)."""
    for _ in range(5):
        consultar_archivo(SHA, config=CONFIG, deps=deps)


@pytest.mark.ac("AC-VT-05")
def test_tras_cinco_fallos_se_abre_y_analiza_sin_llamada() -> None:
    """FR-004: tras 5 fallos el cortacircuitos abre y el análisis continúa (AC-VT-05)."""
    cliente = ClienteDoble()
    deps = deps_prueba(cliente, reloj=RelojFalso())
    _fallar_cinco(deps)
    assert cliente.contar("GET", RUTA) == 5

    sexta = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert sexta.clasificacion == "desconocida"
    assert sexta.fuente == "sin_llamada"
    assert [b.codigo for b in sexta.banderas] == ["VT_NO_DISPONIBLE"]
    assert cliente.contar("GET", RUTA) == 5  # jamás llamó durante la ventana


@pytest.mark.ac("AC-VT-05")
def test_ventana_60_segundos_y_cierre() -> None:
    """La ventana dura 60 s: a los 59 s sigue abierto; a los 60 vuelve a llamarse (FR-004)."""
    cliente = ClienteDoble()
    reloj = RelojFalso()
    deps = deps_prueba(cliente, reloj=reloj)
    _fallar_cinco(deps)

    reloj.avanzar(59.0)
    al_59 = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert cliente.contar("GET", RUTA) == 5
    assert al_59.fuente == "sin_llamada"

    reloj.avanzar(1.0)  # 60 s en total desde la apertura
    cliente.registrar("GET", RUTA, RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json")))
    al_60 = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert al_60.clasificacion == "maliciosa"
    assert cliente.contar("GET", RUTA) == 6


@pytest.mark.ac("AC-VT-05")
def test_un_exito_entre_fallos_reinicia_el_conteo() -> None:
    """Un veredicto concluyente (200/404) pone el contador de fallos a cero (FR-004)."""
    cliente = ClienteDoble()
    reloj = RelojFalso()
    cache = CacheMemoria()
    deps = deps_prueba(cliente, reloj=reloj, cache=cache)

    for _ in range(4):
        consultar_archivo(SHA, config=CONFIG, deps=deps)
    cliente.registrar("GET", RUTA, RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json")))
    exito = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert exito.clasificacion == "maliciosa"

    # Se vacía la caché para que las próximas consultas vuelvan a red (mismo circuito).
    cache.limpiar()
    for _ in range(4):
        consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert cliente.contar("GET", RUTA) == 9  # 4 + 1 + 4 intentos reales al transporte

    # 4 fallos tras el éxito no alcanzan el umbral: el circuito sigue cerrado.
    cliente.registrar("GET", RUTA, RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json")))
    tras_nueve = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert tras_nueve.clasificacion == "maliciosa"
    assert cliente.contar("GET", RUTA) == 10
