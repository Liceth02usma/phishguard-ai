"""Integración con VirusTotal API v3 (spec 006, módulo M06).

Cliente determinista para archivos (SHA-256), URLs (id Base64 url-safe sin
relleno), dominios e IPs: clasifica con la tabla M06.4, limita a la cuota
pública (4/min, 500/día), reintenta 429/5xx (1/2/4 s + jitter), abre un
cortacircuitos a los 5 fallos (60 s), cachea SOLO veredictos reales (7 d /
24 h / 1 h) y respeta el presupuesto de 10 consultas por correo. API
síncrona (D2); sin wiring al pipeline — lo consumen las specs 007/008.

API pública (contrato `contracts/virustotal-api.md`):
- `consultar_archivo` / `consultar_url` / `consultar_dominio` / `consultar_ip`
- `subir_archivo` / `enviar_url_desconocida` (detrás de flags, default false)
- `clasificar_stats` (tabla pura FR-007) y `presupuesto_nuevo`
- `ConfigVT` / `ConfiguracionError` / `DependenciasVT` / `dependencias_por_defecto`
- `ResultadoVT` / `BanderaVT` / `LastAnalysisStats` / `EntradaCache` / `Presupuesto`
- `CATALOGO_VT` (catálogos 5.2/5.3, Art. VI.2)
"""

from __future__ import annotations

from src.level2_agent.virustotal.clasificacion import clasificar_stats
from src.level2_agent.virustotal.cliente import (
    consultar_archivo,
    consultar_dominio,
    consultar_ip,
    consultar_url,
)
from src.level2_agent.virustotal.configuracion import ConfiguracionError, ConfigVT
from src.level2_agent.virustotal.envios import enviar_url_desconocida, subir_archivo
from src.level2_agent.virustotal.modelos import (
    CATALOGO_VT,
    BanderaVT,
    EntradaCache,
    LastAnalysisStats,
    ResultadoVT,
)
from src.level2_agent.virustotal.presupuesto import Presupuesto, presupuesto_nuevo
from src.level2_agent.virustotal.puertos import (
    ClienteHTTPVT,
    DependenciasVT,
    RepositorioCacheVT,
    RepositorioContadorVT,
    RespuestaVT,
    dependencias_por_defecto,
)

__all__ = [
    "CATALOGO_VT",
    "BanderaVT",
    "ClienteHTTPVT",
    "ConfigVT",
    "ConfiguracionError",
    "DependenciasVT",
    "EntradaCache",
    "LastAnalysisStats",
    "Presupuesto",
    "RepositorioCacheVT",
    "RepositorioContadorVT",
    "RespuestaVT",
    "ResultadoVT",
    "clasificar_stats",
    "consultar_archivo",
    "consultar_dominio",
    "consultar_ip",
    "consultar_url",
    "dependencias_por_defecto",
    "enviar_url_desconocida",
    "presupuesto_nuevo",
    "subir_archivo",
]
