"""Configuración compartida de pytest para las pruebas de las compuertas.

Registra el marker `ac` (Art. II.6) y expone helpers para generar archivos
de prueba temporales, además de los dobles del agente ReAct usados por la
spec 001 (Art. II.5 — sin red real).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

# Respuesta determinista del doble del agente ReAct (spec 001, research D7).
REPORTE_FALSO = {
    "resumen": "Análisis del correo bajo revisión por el agente.",
    "analisis_tecnico": "Evidencia contrastada con marcos NIST y OWASP por el doble.",
    "indicadores_phishing": ["patron_sospechoso_uno", "patron_sospechoso_dos"],
    "es_phishing": True,
    "nivel_severidad": "Medio",
    "justificacion_veredicto": "Respuesta fija del doble para pruebas deterministas.",
}


def pytest_configure(config: pytest.Config) -> None:
    """Registra el marker ac si no está registrado."""
    config.addinivalue_line(
        "markers",
        "ac(id): asocia una prueba a un criterio de aceptación AC-XXX-NN",
    )


@pytest.fixture
def tmp_py_file(tmp_path: Path) -> Iterator[Path]:
    """Factory para crear un archivo .py temporal con N líneas.

    Yields una función `crear(lineas: int, nombre="mod.py") -> Path`.
    """
    def crear(lineas: int, nombre: str = "mod.py") -> Path:
        ruta = tmp_path / nombre
        contenido = "\n".join(f"x = {i}" for i in range(lineas)) + "\n"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    yield crear  # type: ignore[misc]


class _AgenteReActFalso:
    """Doble del agente ReAct: mismo input → misma respuesta JSON (sin red)."""

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el reporte fijo en el formato que consume analyze_email."""
        from langchain_core.messages import AIMessage

        contenido = json.dumps(REPORTE_FALSO, ensure_ascii=False)
        return {"messages": [AIMessage(content=contenido)]}


@pytest.fixture
def agente_react_falso(monkeypatch: pytest.MonkeyPatch) -> _AgenteReActFalso:
    """Sustituye LLM y agente por dobles deterministas (sin API key ni red)."""
    import src.level2_agent.agent as mod_agent

    monkeypatch.setattr(mod_agent, "_ensure_llm", lambda: None)
    agente = _AgenteReActFalso()
    monkeypatch.setattr(mod_agent, "_get_react_agent", lambda: agente)
    return agente


@pytest.fixture
def sin_red_jira(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sustituye create_jira_ticket por un stub sin efectos externos."""
    import src.level2_agent.agent as mod_agent

    monkeypatch.setattr(
        mod_agent, "create_jira_ticket", lambda reporte: {"simulado": True}
    )


@pytest.fixture
def entorno_sin_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina MONGODB_ATLAS_CLUSTER_URI del entorno de la prueba.

    Mecanismo de rojo de AC-MEM-02 (research D7): con el código actual, la
    ruta del agente llama a get_chat_history y lanza ValueError.
    """
    monkeypatch.delenv("MONGODB_ATLAS_CLUSTER_URI", raising=False)


# --- Fábrica de correos .eml para la spec 002 (AC-NORM-01..06, Art. II.5) ---


@pytest.fixture
def fabrica_eml() -> Callable[..., bytes]:
    """Devuelve una función que construye bytes `.eml` (multipart) parametrizable.

    El builder permite controlar cabeceras repetidas (`received`), cuerpos
    HTML/texto, adjuntos y cabeceras extra, para alimentar los AC de
    normalización sin red.
    """
    import email as _email
    from email.message import EmailMessage

    def construir(
        *,
        received: Sequence[str] = ("via mail;1",),
        html: str | None = None,
        texto: str | None = "cuerpo de texto",
        adjuntos: Sequence[tuple[str, str, bytes]] = (),
        cabeceras_extra: Sequence[tuple[str, str]] = (),
        asunto: str = "Asunto de prueba",
        remitente: str = "juan.perez@empresa.com",
        destinatario: str = "destino@empresa.com",
        message_id: str = "<msg-prueba@empresa.com>",
    ) -> bytes:
        """Construye un `.eml` en bytes con la estructura pedida."""
        msg = EmailMessage()
        msg["From"] = remitente
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg["Message-ID"] = message_id
        for valor in received:
            msg["Received"] = valor
        for nombre, valor in cabeceras_extra:
            msg[nombre] = valor

        partes_texto = texto is not None
        partes_html = html is not None
        if partes_texto and partes_html:
            msg.set_content(texto)
            msg.add_alternative(html, subtype="html")
        elif partes_texto:
            msg.set_content(texto)
        elif partes_html:
            msg.set_content(html, subtype="html")
        for nombre, tipo, payload in adjuntos:
            maintype, subtype = tipo.split("/", 1)
            msg.add_attachment(payload, maintype=maintype, subtype=subtype, filename=nombre)

        return msg.as_bytes(policy=_email.policy.default)

    return construir


@pytest.fixture
def fabrica_html_oculto() -> Callable[[str], str]:
    """Devuelve una función que envuelve HTML con script, comentario y texto oculto."""

    def construir(visible: str) -> str:
        return (
            "<html><head><style>.x{color:red}</style></head>"
            "<body>"
            "<script>alert('x')</script>"
            "<!-- comentario oculto -->"
            f"<p style='display:none'>{visible}-oculto</p>"
            f"<p style='font-size:0'>{visible}-cero</p>"
            f"<a href='https://ejemplo.com'>{visible}</a>"
            "</body></html>"
        )

    return construir


# --- Fábrica de correos EmailData para la spec 003 (AC-HDR-01..06, Art. II.5) ---


@pytest.fixture
def construir_correo() -> Callable[..., Any]:
    """Devuelve una función que construye ``EmailData`` con cabeceras dadas.

    El builder permite controlar las cabeceras (Authentication-Results, From,
    Reply-To, Return-Path, Message-ID, Date, Received) y los campos normalizados
    (asunto, texto_limpio), para alimentar las banderas sin red (Art. II.5).
    """
    from src.level2_agent.models import Cabecera, EmailData

    def construir(
        *,
        cabeceras: Sequence[tuple[str, str]] = (),
        asunto: str = "",
        message_id: str = "",
        texto_limpio: str = "",
    ) -> Any:
        return EmailData(
            cabeceras=[Cabecera(nombre=n, valor=v) for n, v in cabeceras],
            subject=asunto,
            message_id=message_id,
            texto_limpio=texto_limpio,
        )

    return construir


# --- Dobles de RDAP para la spec 003 (AC-HDR-06, Art. II.5: sin red real) ---


class _ClienteRDAPNulo:
    """Doble que simula RDAP caido: devuelve ``None`` sin excepcion."""

    def registrar_evento(self, dominio: str) -> None:
        return None


@pytest.fixture
def rdap_nulo() -> _ClienteRDAPNulo:
    """Cliente RDAP que nunca devuelve fecha (fallo)."""
    return _ClienteRDAPNulo()


@pytest.fixture
def rdap_fijo() -> Any:
    """Factory de clientes RDAP que devuelven siempre la misma fecha de registro."""

    def crear(fecha: Any) -> Any:
        class _Cliente:
            def registrar_evento(self, dominio: str) -> Any:
                return fecha

        return _Cliente()

    return crear
