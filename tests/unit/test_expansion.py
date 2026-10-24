"""Tabla de decisión de la máquina de estados de expansión (research D9).

`expandir_acortador` debe recorrer exactamente los estados del data-model:
no_acortadora, reputacion_conocida, esquema_no_permitido, expandida,
limite_saltos, limite_tiempo, bloqueada_ssrf y error_controlado — y nunca
emitir más de `TOPE_SALTOS` peticiones (I7).
"""

from __future__ import annotations

from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.expansion import expandir_acortador
from src.level2_agent.analisis_urls.modelos import TOPE_SALTOS

from dobles_red import (
    ClienteHTTPDouble,
    DependenciasURLs,
    RelojFalso,
    ResolvedorDNSDouble,
    deps_de_prueba,
)
from dobles_red import RespuestaRedireccion as Respuesta

_CONFIG = ConfigURLs(acortadores=frozenset({"corto.test"}))


def _deps(
    http: ClienteHTTPDouble, reloj: RelojFalso | None = None
) -> DependenciasURLs:
    """Deps con DNS que resuelve el acortador y el destino final a IP pública."""
    dns = ResolvedorDNSDouble(
        {"corto.test": ["93.184.216.34"], "final.example": ["93.184.216.35"]}
    )
    return deps_de_prueba(resolvedor=dns, http=http, reloj=reloj)


class _CacheLlena:
    """Doble de caché VT: todo es conocido (FR-006)."""

    def conoce(self, url_saneada: str) -> bool:
        """Siempre True: la reputación ya se conoce, no se expande."""
        return True


def test_no_acortadora_no_toca_puertos() -> None:
    """Host fuera de la lista ⇒ no_acortadora y CERO llamadas a DNS/HTTP."""
    dns = ResolvedorDNSDouble()
    doble = ClienteHTTPDouble()

    resultado = expandir_acortador(
        "http://example.com/x", _CONFIG, deps_de_prueba(resolvedor=dns, http=doble)
    )

    assert resultado.estado == "no_acortadora"
    assert dns.consultas == []
    assert doble.peticiones == []
    assert resultado.saltos == 0


def test_reputacion_conocida_no_expande() -> None:
    """FR-006: si la caché conoce la URL, no hay conexión directa."""
    doble = ClienteHTTPDouble()
    deps = _deps(doble)
    deps_con_cache = DependenciasURLs(
        resolvedor=deps.resolvedor,
        http=deps.http,
        cache=_CacheLlena(),
        rdap=deps.rdap,
        reloj=deps.reloj,
    )

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, deps_con_cache)

    assert resultado.estado == "reputacion_conocida"
    assert doble.peticiones == []


def test_esquema_no_permitido() -> None:
    """Solo http/https (FR-003): ftp queda rechazado sin tocar red."""
    doble = ClienteHTTPDouble()

    resultado = expandir_acortador("ftp://corto.test/x", _CONFIG, _deps(doble))

    assert resultado.estado == "esquema_no_permitido"
    assert doble.peticiones == []


def test_falla_de_dns_es_error_controlado() -> None:
    """DNS irresoluble ⇒ error_controlado, sin excepción (III.9, AC-URL-07)."""
    dns = ResolvedorDNSDouble()  # sin mapping: lanza OSError

    resultado = expandir_acortador(
        "http://corto.test/x", _CONFIG, deps_de_prueba(resolvedor=dns)
    )

    assert resultado.estado == "error_controlado"
    assert resultado.motivo


def test_status_4xx_es_error_controlado() -> None:
    """Un 404 no es destino: error_controlado con el salto contado."""
    doble = ClienteHTTPDouble([Respuesta(status=404, location=None)])

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble))

    assert resultado.estado == "error_controlado"
    assert resultado.saltos == 1
    assert "404" in (resultado.motivo or "")


def test_3xx_sin_location_es_error_controlado() -> None:
    """Una redirección sin Location es intratable: error_controlado."""
    doble = ClienteHTTPDouble([Respuesta(status=302, location=None)])

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble))

    assert resultado.estado == "error_controlado"
    assert "location" in (resultado.motivo or "").lower()


def test_200_directo_es_expandida() -> None:
    """200 en la primera petición ⇒ expandida con destino = la propia URL."""
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble))

    assert resultado.estado == "expandida"
    assert resultado.destino_final == "http://corto.test/x"
    assert resultado.saltos == 1


def test_3xx_a_no_acortador_es_expandida() -> None:
    """Seguir está prohibido fuera de la lista: el destino no-acortador es el final."""
    doble = ClienteHTTPDouble([Respuesta(status=302, location="http://final.example/z")])

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble))

    assert resultado.estado == "expandida"
    assert resultado.destino_final == "http://final.example/z"
    assert len(doble.peticiones) == 1


def test_nunca_mas_de_tope_saltos() -> None:
    """Redirecciones infinitas al mismo acortador: jamás se pide un 6.º salto."""
    reloj = RelojFalso()

    def _siempre(_url: str) -> Respuesta:
        reloj.avanzar(0.1)
        return Respuesta(status=302, location="http://corto.test/p2")

    doble = ClienteHTTPDouble([_siempre] * 9)
    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble, reloj))

    assert resultado.estado == "limite_saltos"
    assert len(doble.peticiones) == TOPE_SALTOS == resultado.saltos


def test_duracion_ms_usa_el_reloj_inyectado() -> None:
    """La duración proviene del reloj inyectado, no del tiempo real (D15)."""
    reloj = RelojFalso()
    doble = ClienteHTTPDouble([Respuesta(status=200, location=None)])

    resultado = expandir_acortador("http://corto.test/x", _CONFIG, _deps(doble, reloj))

    assert resultado.duracion_ms == 0
    assert reloj() == 0.0
