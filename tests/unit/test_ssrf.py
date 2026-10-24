"""Matriz SSRF sobre `REDES_PROHIBIDAS` (FR-004, research D7, invariante I1).

Cada una de las 8 redes del spec (IPv4 e IPv6) debe bloquearse; las IPs
públicas pasan; `is_global` añade defensa en profundidad (0.0.0.0/8,
multicast, reservadas). Un host con MIXTO público+privado se bloquea entero.
"""

from __future__ import annotations

from ipaddress import ip_address

import pytest
from src.level2_agent.analisis_urls.ssrf import ip_permitida, validar_host

from dobles_red import ResolvedorDNSDouble

PROHIBIDAS = [
    "10.1.2.3",  # 10.0.0.0/8
    "172.16.5.5",  # 172.16.0.0/12
    "192.168.10.10",  # 192.168.0.0/16
    "127.0.0.1",  # 127.0.0.0/8 loopback
    "169.254.169.254",  # 169.254.0.0/16 metadatos de nube
    "::1",  # loopback IPv6
    "fc00::1",  # fc00::/7 privada IPv6
    "fe80::1",  # fe80::/10 enlace local IPv6
]

PUBLICAS = ["8.8.8.8", "93.184.216.34", "2606:4700::1111"]

ADICIONALES_BLOQUEADAS = [
    "0.0.0.0",  # reservada (is_global False)
    "224.0.0.1",  # multicast (is_global False)
]


@pytest.mark.parametrize("ip", PROHIBIDAS)
def test_redes_fr004_bloqueadas(ip: str) -> None:
    """Las 8 redes literales de FR-004 están prohibidas."""
    assert ip_permitida(ip_address(ip)) is False


@pytest.mark.parametrize("ip", PUBLICAS)
def test_ips_publicas_permitidas(ip: str) -> None:
    """Las IPs públicas pasan la validación."""
    assert ip_permitida(ip_address(ip)) is True


@pytest.mark.parametrize("ip", ADICIONALES_BLOQUEADAS)
def test_defensa_en_profundidad_is_global(ip: str) -> None:
    """`is_global` bloquea además reservadas y multicast (research D7)."""
    assert ip_permitida(ip_address(ip)) is False


def test_host_mixto_publico_y_privado_se_bloquea() -> None:
    """Si CUALQUIERA de las IPs resueltas es privada, el host entero se bloquea."""
    dns = ResolvedorDNSDouble({"mixto.test": ["93.184.216.34", "10.0.0.5"]})

    permitido, motivo = validar_host("mixto.test", dns)

    assert permitido is False
    assert "10.0.0.5" in (motivo or "")


def test_host_publico_total_pasa() -> None:
    """Un host resuelto solo a IPs públicas pasa la validación."""
    dns = ResolvedorDNSDouble({"bien.test": ["93.184.216.34", "2606:4700::1111"]})

    permitido, motivo = validar_host("bien.test", dns)

    assert permitido is True
    assert motivo is None


def test_ip_literal_no_consulta_dns() -> None:
    """Una IP literal se valida directamente sin resolver (sin llamada al puerto)."""
    dns = ResolvedorDNSDouble()

    permitido, _ = validar_host("127.0.0.1", dns)
    assert permitido is False
    assert dns.consultas == []


def test_falla_de_dns_propaga_error() -> None:
    """DNS irresoluble lanza OSError para que el motor lo mapee a error_controlado."""
    dns = ResolvedorDNSDouble()

    with pytest.raises(OSError):
        validar_host("desconocido.test", dns)
