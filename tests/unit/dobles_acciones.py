"""Dobles de prueba para el ejecutor de acciones (spec 010).

GmailDoble y JiraDoble trackean llamadas sin tocar servicios reales.
entrada_acciones_ejemplo() construye una EntradaAcciones mínima.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.level2_agent.acciones.gmail_adapter import GmailAdapter
from src.level2_agent.acciones.jira_adapter import JiraAdapter
from src.level2_agent.acciones.modelos import (
    Accion,
    EntradaAcciones,
    ResultadoJira,
)
from src.level2_agent.models import PhishingReport


class GmailDoble:
    """Adapter simulado de Gmail que trackea llamadas."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, ...]] = []

    def etiquetar(self, msg_id: str, etiqueta: str) -> str:
        self.llamadas.append(("etiquetar", msg_id, etiqueta))
        return "label_123"

    def archivar(self, msg_id: str) -> None:
        self.llamadas.append(("archivar", msg_id))

    def marcar_leido(self, msg_id: str) -> None:
        self.llamadas.append(("marcar_leido", msg_id))

    def crear_etiqueta(self, nombre: str) -> str:
        self.llamadas.append(("crear_etiqueta", nombre))
        return "label_123"


class JiraDoble:
    """Adapter simulado de Jira que trackea llamadas.

    Por defecto buscar_por_huella retorna None (no existe ticket previo).
    Se puede configurar para simular fallos.
    """

    def __init__(
        self,
        *,
        fallar: bool = False,
        ticket_existente: str | None = None,
    ) -> None:
        self.llamadas: list[tuple[str, ...]] = []
        self._fallar = fallar
        self._ticket_existente = ticket_existente
        self._next_key = 1

    def crear_ticket(self, campos: dict) -> ResultadoJira:
        self.llamadas.append(("crear_ticket", str(campos)))
        if self._fallar:
            raise ConnectionError("Jira no disponible")
        key = f"TEST-{self._next_key}"
        self._next_key += 1
        return ResultadoJira(exito=True, issue_key=key, url=f"https://jira.test/{key}")

    def buscar_por_huella(self, huella: str) -> str | None:
        self.llamadas.append(("buscar_por_huella", huella))
        return self._ticket_existente

    def vincular(self, key_origen: str, key_destino: str) -> None:
        self.llamadas.append(("vincular", key_origen, key_destino))


def entrada_acciones_ejemplo(
    *,
    veredicto: str = "malicioso",
    message_id: str = "msg_test_001",
    remitente: str = "attacker@evil.com",
    asunto: str = "Urgente: verifique su cuenta",
    urls: list[str] | None = None,
    origen: str = "gmail",
) -> EntradaAcciones:
    """Construye una EntradaAcciones mínima con valores por defecto."""
    return EntradaAcciones(
        veredicto=veredicto,  # type: ignore[arg-type]
        nivel_severidad="Alto",
        message_id=message_id,
        remitente=remitente,
        asunto=asunto,
        urls=urls or [],
        reporte=PhishingReport(
            resumen="Phishing detectado",
            analisis_tecnico="Análisis técnico",
            indicadores_phishing=["url_sospechosa"],
            es_phishing=True,
            nivel_severidad="Alto",
            justificacion_veredicto="URL sospechosa",
        ),
        origen=origen,  # type: ignore[arg-type]
    )
