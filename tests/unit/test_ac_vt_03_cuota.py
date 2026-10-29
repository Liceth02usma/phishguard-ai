"""AC-VT-03: 4/min por cubeta, 500/día persistente tras reinicio; se espera u omite."""

from __future__ import annotations

import pytest
from src.level2_agent.virustotal import (
    ConfigVT,
    DependenciasVT,
    consultar_archivo,
    presupuesto_nuevo,
)
from src.level2_agent.virustotal.cache import ContadorMemoria

from dobles_vt import (
    ClienteDoble,
    DormirFalso,
    RelojFalso,
    RespuestaDoble,
    cargar_respuesta,
    deps_prueba,
)

SHA = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


def _deps(cliente: ClienteDoble) -> tuple[DependenciasVT, DormirFalso]:
    """Dependencias de prueba con acceso directo al dormir falso (esperas)."""
    reloj = RelojFalso()
    dormir = DormirFalso(reloj)
    return deps_prueba(cliente, reloj=reloj, dormir=dormir), dormir


def _sha(n: int) -> str:
    """Hash hexadecimal de 64 caracteres determinista por índice de prueba."""
    return f"{n:064x}"


def _cliente(cantidad: int) -> ClienteDoble:
    """Registra rutas para `cantidad` hashes distintos con respuesta 200."""
    cuerpo = cargar_respuesta("archivo_maliciosa.json")
    return ClienteDoble(
        rutas={
            ("GET", f"/files/{_sha(i)}"): [RespuestaDoble(200, cuerpo)]
            for i in range(cantidad)
        }
    )


@pytest.mark.ac("AC-VT-03")
def test_quinta_consulta_espera_la_ventana_de_minuto() -> None:
    """Con la clave pública (4/min) la 5ª consulta espera hasta reponer la ventana (FR-002)."""
    cliente = _cliente(5)
    deps, dormir = _deps(cliente)
    config = ConfigVT(api_key="clave-de-prueba")
    for i in range(5):
        consultar_archivo(_sha(i), config=config, deps=deps)
    assert len(dormir.esperas) == 1
    assert dormir.esperas[0] == pytest.approx(60.0)
    assert sum(1 for p in cliente.peticiones if p.metodo == "GET") == 5


@pytest.mark.ac("AC-VT-03")
def test_presupuesto_agotado_omite_sin_espera() -> None:
    """Con presupuesto agotado la consulta se omite: sin llamada, sin espera (FR-006)."""
    cliente = _cliente(5)
    deps, dormir = _deps(cliente)
    config = ConfigVT(api_key="clave-de-prueba", max_por_correo=4)
    presupuesto = presupuesto_nuevo(config)  # compartido entre las consultas del correo
    for i in range(4):
        consultar_archivo(_sha(i), config=config, deps=deps, presupuesto=presupuesto)
    quinta = consultar_archivo(_sha(4), config=config, deps=deps, presupuesto=presupuesto)
    assert quinta.clasificacion == "desconocida"
    assert quinta.fuente == "sin_llamada"
    assert [b.codigo for b in quinta.banderas] == ["VT_PRESUPUESTO_AGOTADO"]
    assert dormir.esperas == []
    assert cliente.contar("GET", f"/files/{_sha(4)}") == 0


@pytest.mark.ac("AC-VT-03")
def test_cuota_diaria_500_persiste_tras_reinicio() -> None:
    """El contador diario sobrevive al «reinicio»: el consulta 501 no llega a red (FR-002)."""
    almacen: dict[str, int] = {}
    primer_proceso = ContadorMemoria(tope=500, almacen=almacen)
    for _ in range(500):
        assert primer_proceso.consumir("2026-01-01") is True
    assert primer_proceso.consumir("2026-01-01") is False

    # «Reinicio»: proceso nuevo, mismo almacén persistente (vt_contador en Mongo).
    cliente = ClienteDoble()
    reloj = RelojFalso()
    deps = deps_prueba(cliente, contador=ContadorMemoria(tope=500, almacen=almacen), reloj=reloj)
    resultado = consultar_archivo(SHA, config=ConfigVT(api_key="k"), deps=deps)
    assert resultado.clasificacion == "desconocida"
    assert resultado.fuente == "sin_llamada"
    assert [b.codigo for b in resultado.banderas] == ["VT_NO_DISPONIBLE"]
    assert cliente.peticiones == []
