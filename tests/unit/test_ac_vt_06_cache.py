"""AC-VT-06: caché por tipo (7 d / 24 h / 1 h) en proceso, reinicio y resultados reales."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo, consultar_url
from src.level2_agent.virustotal.cache import CacheMemoria
from src.level2_agent.virustotal.identificadores import id_url_base64
from src.level2_agent.virustotal.modelos import EntradaCache
from tests.unit.dobles_vt import (
    ClienteDoble,
    RelojFalso,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
URL = "https://ejemplo.com/ruta/archivo?x=1"
CONFIG = ConfigVT(api_key="clave-de-prueba")
SEGUNDOS_DIA = 86400.0


def _cliente_archivo(cliente: ClienteDoble) -> None:
    """Registra la respuesta 200 para el hash de prueba."""
    cliente.registrar(
        "GET", f"/files/{SHA}", RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
    )


@pytest.mark.ac("AC-VT-06")
def test_segunda_consulta_idéntica_es_cache_sin_llamada() -> None:
    """Mismo hash dos veces → segunda desde caché, sin segunda petición (FR-005)."""
    cliente = ClienteDoble()
    _cliente_archivo(cliente)
    deps = deps_prueba(cliente, reloj=RelojFalso())
    primera = consultar_archivo(SHA, config=CONFIG, deps=deps)
    segunda = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert primera.fuente == "red"
    assert segunda.fuente == "cache"
    assert segunda.consultas_externas == 0
    assert segunda.clasificacion == "maliciosa"
    assert cliente.contar("GET", f"/files/{SHA}") == 1


@pytest.mark.ac("AC-VT-06")
def test_archivo_vigilado_6d23h_y_vencido_7d() -> None:
    """TTL de archivo: 6 d 23 h → caché; 7 d exactos → vencida, nueva llamada (FR-005)."""
    cliente = ClienteDoble()
    _cliente_archivo(cliente)
    reloj = RelojFalso()
    deps = deps_prueba(cliente, reloj=reloj)
    consultar_archivo(SHA, config=CONFIG, deps=deps)

    reloj.avanzar(6 * SEGUNDOS_DIA + 23 * 3600.0)
    al_dia_seis = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert al_dia_seis.fuente == "cache"
    assert cliente.contar("GET", f"/files/{SHA}") == 1

    reloj.avanzar(3600.0)  # 7 d exactos desde el guardado
    a_los_siete = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert a_los_siete.fuente == "red"
    assert cliente.contar("GET", f"/files/{SHA}") == 2


@pytest.mark.ac("AC-VT-06")
def test_url_23h_cache_y_24h_vencida() -> None:
    """TTL de URL: 23 h → caché; 24 h exactas → vencida (FR-005)."""
    identificador = id_url_base64(URL)
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/urls/{identificador}"): [
                RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
            ]
        }
    )
    reloj = RelojFalso()
    deps = deps_prueba(cliente, reloj=reloj)
    consultar_url(URL, config=CONFIG, deps=deps)

    reloj.avanzar(23 * 3600.0)
    al_dia = consultar_url(URL, config=CONFIG, deps=deps)
    assert al_dia.fuente == "cache"

    reloj.avanzar(3600.0)  # 24 h exactas
    a_las_veinticuatro = consultar_url(URL, config=CONFIG, deps=deps)
    assert a_las_veinticuatro.fuente == "red"
    assert cliente.contar("GET", f"/urls/{identificador}") == 2


@pytest.mark.ac("AC-VT-06")
def test_404_caché_1h_y_vencido_60min() -> None:
    """El 404 se cachea como desconocida por 1 h; a los 60 min exactos vence (FR-005)."""
    cliente = ClienteDoble(
        rutas={
            ("GET", f"/files/{SHA}"): [
                RespuestaDoble(404, cargar_respuesta("no_encontrado.json"))
            ]
        }
    )
    reloj = RelojFalso()
    deps = deps_prueba(cliente, reloj=reloj)
    primera = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert primera.clasificacion == "desconocida"

    reloj.avanzar(59 * 60.0)
    al_cincuenta_y_nueve = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert al_cincuenta_y_nueve.fuente == "cache"
    assert cliente.contar("GET", f"/files/{SHA}") == 1

    reloj.avanzar(60.0)  # 60 min exactos
    a_los_sesenta = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert a_los_sesenta.fuente == "red"
    assert cliente.contar("GET", f"/files/{SHA}") == 2


@pytest.mark.ac("AC-VT-06")
def test_reinicio_del_proceso_con_repositorio_compartido() -> None:
    """Nuevo proceso, mismo vt_cache (Mongo): el veredicto se sirve desde caché (FR-005)."""
    almacen: dict[str, EntradaCache] = {}
    cache_1 = CacheMemoria(almacen=almacen)
    cliente_1 = ClienteDoble()
    _cliente_archivo(cliente_1)
    deps_1 = deps_prueba(cliente_1, reloj=RelojFalso(), cache=cache_1)
    consultar_archivo(SHA, config=CONFIG, deps=deps_1)

    cliente_2 = ClienteDoble()  # sin rutas: cualquier llamada fallaría la prueba
    cache_2 = CacheMemoria(almacen=almacen)
    deps_2 = deps_prueba(cliente_2, reloj=RelojFalso(), cache=cache_2)
    tras_reinicio = consultar_archivo(SHA, config=CONFIG, deps=deps_2)
    assert tras_reinicio.fuente == "cache"
    assert tras_reinicio.clasificacion == "maliciosa"
    assert cliente_2.peticiones == []


@pytest.mark.ac("AC-VT-06")
def test_solo_veredictos_reales_se_cachean() -> None:
    """Clarify FR-005: fallos transitorios NO se cachean → recuperación inmediata."""
    # Cortacircuitos abierto → VT_NO_DISPONIBLE sin llamada y sin guardar nada.
    cliente = ClienteDoble()
    reloj = RelojFalso()
    deps = deps_prueba(cliente, reloj=reloj)
    for _ in range(5):
        consultar_archivo(SHA, config=CONFIG, deps=deps)
    transitoria = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert transitoria.fuente == "sin_llamada"

    # Recuperación inmediata: vencida la ventana, se consulta y se cachea el veredicto real.
    reloj.avanzar(60.0)
    cliente.registrar(
        "GET",
        f"/files/{SHA}",
        RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json")),
    )
    recuperada = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert recuperada.clasificacion == "maliciosa"
    desde_cache = consultar_archivo(SHA, config=CONFIG, deps=deps)
    assert desde_cache.fuente == "cache"
