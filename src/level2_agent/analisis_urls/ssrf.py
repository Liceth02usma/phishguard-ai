"""Control SSRF: validación de IPs en cada salto (FR-004, research D7, I1).

Reglas: las redes literales de FR-004 están prohibidas Y, como defensa en
profundidad (Art. V.5), también se rechaza cualquier IP no-global (cubre
`0.0.0.0/8`, multicast y reservadas que FR-004 enumera como "lista").
"""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address

from src.level2_agent.analisis_urls.modelos import REDES_PROHIBIDAS
from src.level2_agent.analisis_urls.puertos import ResolvedorDNS


def ip_permitida(ip: IPv4Address | IPv6Address) -> bool:
    """True solo si la IP pasa las redes de FR-004 y es utilizable como destino público."""
    if any(ip in red for red in REDES_PROHIBIDAS):
        return False
    # Defensa en profundidad: Python marca multicast como "global", así que se
    # excluye explícitamente multicast, reservadas y no especificadas además
    # de las no-globales (0.0.0.0/8, enlace local, etc.).
    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False
    return ip.is_global


def validar_host(host: str, resolvedor: ResolvedorDNS) -> tuple[bool, str | None]:
    """Valida TODAS las IPs del host antes de conectar (literal o vía DNS).

    Una IP literal se valida sin consultar el puerto; cualquier IP prohibida
    bloquea el host entero. Si el DNS falla, propaga `OSError` para que el
    motor lo mapee a `error_controlado` (III.9, AC-URL-07).
    """
    try:
        ips: list[IPv4Address | IPv6Address] = [ip_address(host)]
    except ValueError:
        ips = resolvedor.resolver(host)
    if not ips:
        return False, "dns_sin_ip"
    for ip in ips:
        if not ip_permitida(ip):
            return False, f"ip_bloqueada: {ip}"
    return True, None
