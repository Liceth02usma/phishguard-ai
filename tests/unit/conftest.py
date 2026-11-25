"""Configuración compartida de pytest para las pruebas de las compuertas.

Registra el marker `ac` (Art. II.6) y expone helpers para generar archivos
de prueba temporales, además de los dobles del agente ReAct usados por la
spec 001 (Art. II.5 — sin red real).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

# Respuesta determinista del doble del agente ReAct (spec 001, research D7).
REPORTE_FALSO: dict[str, Any] = {
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
    """Doble del agente: mismo input → misma respuesta (determinista, sin red).

    Auditoría 2026-11-17: el ReAct original se eliminó en spec 009; ahora el
    fixture sustituye `consultar_agente` (el import que hace
    `_agente_zona_gris` en tiempo de llamada) con un ResultadoAgente fijo.
    """

    def __init__(self) -> None:
        from src.level2_agent.agente.modelos import ResultadoAgente, SalidaAgente

        self.resultado = ResultadoAgente(
            salida=SalidaAgente(
                resumen=REPORTE_FALSO["resumen"],
                analisis_tecnico=REPORTE_FALSO["analisis_tecnico"],
                es_phishing=REPORTE_FALSO["es_phishing"],
                indicadores_phishing=list(REPORTE_FALSO["indicadores_phishing"]),
                nivel_severidad=REPORTE_FALSO["nivel_severidad"],
                justificacion_veredicto=REPORTE_FALSO["justificacion_veredicto"],
            ),
            confirmacion_agente=True,
            reintentos=0,
            llamadas_modelo=1,
            razon="exito",
        )

    def __call__(self, entrada: Any, **kwargs: Any) -> Any:
        """Mismo input → mismo resultado fijo (sin red, sin contador real)."""
        return self.resultado


@pytest.fixture
def agente_react_falso(monkeypatch: pytest.MonkeyPatch) -> _AgenteReActFalso:
    """Sustituye consultar_agente por doble determinista (sin API key ni red)."""
    import src.level2_agent.agente as mod_agente

    agente = _AgenteReActFalso()
    monkeypatch.setattr(mod_agente, "consultar_agente", agente)
    return agente


@pytest.fixture
def sin_red_jira(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sustituye create_jira_ticket por un stub sin efectos externos.

    Auditoría 2026-11-17: agent.py ya no llama Jira (spec 009/010); el stub
    se aplica al módulo donde la función aún vive por si algún camino la usa.
    """
    import src.level2_agent.tools.jira_integration as mod_jira

    monkeypatch.setattr(
        mod_jira, "create_jira_ticket", lambda reporte: {"simulado": True}
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


# --- Fábrica de correos con URLs para la spec 004 (AC-URL-01..07, Art. II.5) ---


@pytest.fixture
def fabrica_email_urls() -> Callable[..., Any]:
    """Devuelve una función que construye EmailData con HTML/texto parametrizable.

    Cubre (T008): `href`, `src`, `action`, pares texto→destino, URLs en
    texto plano, tracking, duplicados y variantes malformadas/oversized.
    """

    def construir(
        *, html: str = "", texto: str = "", texto_limpio: str | None = None
    ) -> Any:
        from src.level2_agent.models import EmailData

        limpio = texto if texto_limpio is None else texto_limpio
        return EmailData(htmlBody=html, textBody=texto, texto_limpio=limpio)

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


@pytest.fixture(autouse=True)
def _reiniciar_cache_rdap() -> Iterator[None]:
    """Vacia la cache RDAP de proceso antes de cada prueba (Art. II.5: determinismo)."""
    from src.level2_agent.banderas.rdap import reiniciar_cache_proceso

    reiniciar_cache_proceso()
    yield
    reiniciar_cache_proceso()


@pytest.fixture
def email_enlaces_canonico(fabrica_email_urls: Callable[..., Any]) -> Any:
    """Correo canónico de phishing: enlace engañoso, acortador con PII e IP interna."""
    html = (
        "<html><body>"
        '<a href="http://evil.example/login">https://banco.com</a>'
        '<a href="https://bit.ly/3xAb?utm_source=mail&token=abc123'
        '&email=j.perez@banco.com">Premio</a>'
        '<img src="http://192.168.1.10/logo.png"/>'
        "</body></html>"
    )
    texto = "visita https://banco.com y tambien https://bit.ly/3xAb?utm_source=mail"
    return fabrica_email_urls(html=html, texto=texto)
# --- Fábrica de adjuntos para la spec 005 (AC-ADJ-01..06, Art. II.5, SC-003) ---
# Todo se genera en memoria (io.BytesIO/zipfile): NUNCA se escribe a disco
# con el nombre original (FR-006, SC-003).


@pytest.fixture
def fabrica_pdf() -> Callable[..., bytes]:
    """Devuelve una función que construye PDFs mínimos en memoria.

    generar(catalog_extra="") -> bytes: PDF con extras en el catálogo /Root.
    generar(truncar=True) -> bytes: PDF truncado (inválido).
    """
    def generar(*, catalog_extra: str = "", truncar: bool = False) -> bytes:
        obj1 = f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R {catalog_extra} >>\nendobj\n"
        obj2 = "2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        header = b"%PDF-1.4\n"
        body = (obj1 + obj2).encode("latin-1")
        xref_offset = len(header) + len(body)
        xref = (
            f"xref\n0 3\n"
            f"0000000000 65535 f \n"
            f"{len(header):010d} 00000 n \n"
            f"{len(header) + len(obj1.encode('latin-1')):010d} 00000 n \n"
            f"trailer\n<< /Root 1 0 R /Size 3 >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
        data = header + body + xref
        if truncar:
            return data[: len(data) // 2]
        return data

    return generar


@pytest.fixture
def fabrica_docx() -> Callable[..., bytes]:
    """Devuelve una función que construye docx (OOXML zip) mínimos en memoria.

    generar(archivos_extra={}) -> bytes: docx con archivos adicionales dentro.
    """
    import io as _io
    import zipfile

    def generar(archivos_extra: dict[str, bytes] | None = None) -> bytes:
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "[Content_Types].xml",
                b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                b'<Default Extension="xml" ContentType="text/xml"/></Types>',
            )
            zf.writestr(
                "_rels/.rels",
                b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                b'<Relationship Id="r1"'
                b' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
                b' Target="word/document.xml"/></Relationships>',
            )
            zf.writestr(
                "word/document.xml",
                b'<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><body/></document>',
            )
            if archivos_extra:
                for nombre, contenido in archivos_extra.items():
                    zf.writestr(nombre, contenido)
        return buf.getvalue()

    return generar


@pytest.fixture
def fabrica_zip() -> Callable[..., bytes]:
    """Devuelve una función que construye zips en memoria parametrizable.

    generar(n_entradas=1, contenido=None, cifrado=False, nivel=zipfile.ZIP_DEFLATED)
    -> bytes.
    """
    import io as _io
    import zipfile

    def generar(
        *,
        n_entradas: int = 1,
        contenido: bytes | None = None,
        cifrado: bool = False,
        nivel: int = zipfile.ZIP_DEFLATED,
    ) -> bytes:
        if contenido is None:
            contenido = b"datos de prueba\n" * 10
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", nivel) as zf:
            for i in range(n_entradas):
                info = zipfile.ZipInfo(f"entrada_{i}.txt")
                info.compress_type = nivel
                if cifrado:
                    info.flag_bits |= 0x1  # bit de cifrado (FR-005)
                zf.writestr(info, contenido)
        return buf.getvalue()

    return generar


@pytest.fixture
def exe_mz() -> bytes:
    """Bytes de un ejecutable PE mínimo (firma MZ) para pruebas de tipo real."""
    return b"MZ" + b"\x00" * 100 + b"PE\x00\x00" + b"\x00" * 50


# ---------------------------------------------------------------------------
# Entorno de la suite: sin red real (Art. II.5 — determinismo, cero red)
# ---------------------------------------------------------------------------


class _RDAPSinRed:
    """Cliente RDAP sin red: fecha de registro desconocida al instante.

    Sustituye a ``RequestsRDAP`` como default de ``evaluar_banderas``: cada
    dominio costaba hasta 2 intentos × 5 s de timeout contra rdap.org y
    verisign, sin cache entre pruebas (la cache de proceso se vacía en cada
    test por ``_reiniciar_cache_rdap``).
    """

    def registrar_evento(self, dominio: str) -> None:
        """Nunca consulta ni lanza: ``None`` → banda conservadora (III.9)."""
        return None


@pytest.fixture(autouse=True)
def _entorno_prueba_sin_red(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Aísla cada prueba de la red externa y de los secretos de ``.env``.

    Dos mecanismos, ambos necesarios:

    1. **Variables de entorno con valores benignos.** Se fijan en el arranque
       de cada prueba (``load_dotenv`` no pisa variables ya presentes, así que
       los valores reales del ``.env`` del desarrollador no llegan a los tests):
       - ``LLM_PROVEEDOR=simulado`` → ``SimuladoAdapter``, cero llamadas a
         Gemini/Groq (una llamada real costaba ~80 s por análisis).
       - ``MONGODB_ATLAS_CLUSTER_URI=""`` → repos, contador LLM y retriever
         vectorial caen a memoria (falsy = mismo camino que "ausente").
       - ``VT_API_KEY=""`` → VirusTotal queda ``VT_NO_DISPONIBLE`` sin
         peticiones.
       - ``GOOGLE_API_KEY=""`` → refuerzo si algo lee la clave directamente.
       - ``PYTHON_DOTENV_DISABLED=1`` → ``load_dotenv()`` deja de reinyectar
         el ``.env``: sin esto, una prueba que hace ``delenv("MONGODB_...")``
         era reabastecida con la URI real en el siguiente ``create_app()`` y
         el cliente pymongo se conectaba a Atlas (fuga observada 2026-11-25).

       El resto de claves de ``.env`` (``DOMINIOS_PROPIOS``,
       ``ACCIONES_DRY_RUN``…) sí llegan: se cargan una sola vez al importar
       los módulos durante la recolección, antes de que este fixture corra.

       Se restauran a mano al terminar: algunas pruebas hacen ``pop`` de
       estas claves y el ``undo`` de ``monkeypatch`` fallaría.

    2. **E/S de scoring sustituida por dobles.** ``calcular_score_final`` usa
       dependencias de producción por defecto: DNS real y ``requests.head``
       para expandir acortadores (~12 s bloqueados por URL en un entorno sin
       salida a la red). Se sustituyen por los dobles de ``dobles_red``
       (Art. II.5).
    """
    from src.level3_logic.scoring import motor as scoring_motor

    from dobles_red import deps_de_prueba

    claves = {
        "LLM_PROVEEDOR": "simulado",
        "MONGODB_ATLAS_CLUSTER_URI": "",
        "VT_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "PYTHON_DOTENV_DISABLED": "1",
    }
    previas = {clave: os.environ.get(clave) for clave in claves}
    os.environ.update(claves)

    dependencias_scoring = scoring_motor.DependenciasScoring
    monkeypatch.setattr(
        "src.level2_agent.banderas.motor.RequestsRDAP", _RDAPSinRed
    )
    monkeypatch.setattr(
        scoring_motor,
        "DependenciasScoring",
        lambda: dependencias_scoring(deps_urls=deps_de_prueba()),
    )
    monkeypatch.setattr(
        "src.level2_agent.analisis_urls.motor.dependencias_por_defecto",
        deps_de_prueba,
    )
    try:
        yield
    finally:
        for clave, valor in previas.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor
