"""Limitador: cubeta por minuto (FR-002/M06.1), VT_RPM, VT_DAILY=0 y ficha diaria."""

from __future__ import annotations

import asyncio

import pytest
from src.level2_agent.virustotal import ConfigVT, consultar_archivo
from src.level2_agent.virustotal.cache import ContadorMemoria
from src.level2_agent.virustotal.limitador import Limitador
from tests.unit.dobles_vt import ClienteDoble, DormirFalso, RelojFalso, RespuestaDoble, cargar_respuesta, deps_prueba


def _limitador() -> tuple[Limitador, RelojFalso, DormirFalso]:
    """Limitador con reloj/dormir falsos enlazados entre sí."""
    reloj = RelojFalso()
    dormir = DormirFalso(reloj)
    return Limitador(reloj=reloj, dormir=dormir), reloj, dormir


def _esperar(limitador: Limitador, rpm: int) -> None:
    """Ejecuta la espera de ficha de minuto de forma síncrona para pruebas."""
    asyncio.run(limitador.esperar_ficha(rpm))


@pytest.mark.ac("AC-VT-03")
def test_cubeta_cuatro_fichas_por_ventana() -> None:
    """4 fichas sin esperar; la 5ª espera hasta completar los 60 s (FR-002)."""
    limitador, reloj, dormir = _limitador()
    for _ in range(4):
        _esperar(limitador, 4)
    assert dormir.esperas == []
    _esperar(limitador, 4)
    assert dormir.esperas == [60.0]  # ventana completa desde el inicio


@pytest.mark.ac("AC-VT-03")
def test_frontera_59_sin_reponer_y_60_reponed() -> None:
    """A los 59 s la ventana NO se repone (espera 1 s); a los 60 s sí (FR-002)."""
    limitador, reloj, dormir = _limitador()
    for _ in range(4):
        _esperar(limitador, 4)
    reloj.avanzar(59.0)
    _esperar(limitador, 4)
    assert dormir.esperas == [1.0]  # 60 - 59 = 1 s restante

    limitador_2, reloj_2, dormir_2 = _limitador()
    for _ in range(4):
        _esperar(limitador_2, 4)
    reloj_2.avanzar(60.0)
    _esperar(limitador_2, 4)
    assert dormir_2.esperas == []  # la ventana ya venció: sin dormir


@pytest.mark.ac("AC-VT-03")
def test_vt_rpm_en_premium() -> None:
    """Premium honra VT_RPM configurado explícitamente (clarify FR-002, 10/min)."""
    limitador, _, dormir = _limitador()
    for _ in range(10):
        _esperar(limitador, 10)
    assert dormir.esperas == []
    _esperar(limitador, 10)
    assert len(dormir.esperas) == 1  # la 11ª sí espera


@pytest.mark.ac("AC-VT-03")
def test_vt_daily_cero_desactiva_tope() -> None:
    """VT_DAILY=0 → sin tope diario: el contador no bloquea consultas (D9)."""
    contador = ContadorMemoria(tope=0)
    cliente = ClienteDoble(
        rutas={
            ("GET", "/files/" + "ab" * 32): [
                RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))
            ]
        }
    )
    deps = deps_prueba(cliente, contador=contador)
    config = ConfigVT(api_key="k", tope_dia=0, rpm=1000)
    resultado = consultar_archivo("ab" * 32, config=config, deps=deps)
    assert resultado.consultas_externas == 1
    assert contador.usos("2026-01-01") == 1  # se usó, pero el tope no aplica


@pytest.mark.ac("AC-VT-03")
def test_ficha_diaria_consumida_solo_en_llamadas_a_red() -> None:
    """Cada consulta a red consume 1 uso diario; un acierto de caché consume 0 (FR-005)."""
    contador = ContadorMemoria(tope=500)
    sha = "ab" * 32
    cliente = ClienteDoble(
        rutas={("GET", f"/files/{sha}"): [RespuestaDoble(200, cargar_respuesta("archivo_maliciosa.json"))]}
    )
    deps = deps_prueba(cliente, contador=contador)
    config = ConfigVT(api_key="k", rpm=1000)
    consultar_archivo(sha, config=config, deps=deps)
    assert contador.usos("2026-01-01") == 1
    consultar_archivo(sha, config=config, deps=deps)  # caché
    assert contador.usos("2026-01-01") == 1
    assert cliente.contar("GET", f"/files/{sha}") == 1
