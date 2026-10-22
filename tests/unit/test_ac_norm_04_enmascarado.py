"""AC-NORM-04: lo persistido y lo enviado al modelo no contiene PII sin enmascarar."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.models import EmailData
from src.level2_agent.normalizacion import (
    enmascarar_para_terceros,
    enmascarar_texto,
    normalizar_desde_eml,
)
from src.level2_agent.normalizacion.enmascarado import (
    CONTIENE_CORREO,
    CONTIENE_DIGITOS_LARGOS,
)
from src.level2_agent.normalizacion.limites import (
    LIMITE_ASUNTO_LLM,
    LIMITE_CARACTERES_TEXTO,
    LIMITE_HEADERS_LLM,
    LIMITE_HTML_LLM,
)


@pytest.mark.ac("AC-NORM-04")
def test_html_body_no_se_persiste(fabrica_eml: Callable[..., bytes]) -> None:
    """`htmlBody` queda fuera de `model_dump` (FR-001: solo en memoria)."""
    eml = fabrica_eml(html="<p>hola</p>", texto="hola")
    normalizado = normalizar_desde_eml(eml)
    assert "htmlBody" not in normalizado.model_dump()


@pytest.mark.ac("AC-NORM-04")
def test_vista_terceros_sin_pii_de_cuerpo(fabrica_eml: Callable[..., bytes]) -> None:
    """La vista para terceros enmascara correos y tarjetas del cuerpo y destinatario."""
    eml = fabrica_eml(
        html="<p>mi tarjeta 4111111111111111 y correo juan.perez@empresa.com</p>",
        texto="contacto juan.perez@empresa.com tarjeta 4111-1111-1111-1111",
        destinatario="destino.cliente@empresa.com",
    )
    normalizado = normalizar_desde_eml(eml)
    vista = enmascarar_para_terceros(normalizado)

    # Los correos del cuerpo/destinatario quedan enmascarados (primera letra + ***).
    assert "juan.perez@empresa.com" not in vista.texto_limpio
    assert "j***@empresa.com" in vista.texto_limpio
    assert "destino.cliente@empresa.com" not in vista.recipient
    assert "d***@empresa.com" in vista.recipient
    # Las secuencias de dígitos quedan ocultas.
    assert "4111111111111111" not in vista.texto_limpio
    assert CONTIENE_DIGITOS_LARGOS.search(vista.texto_limpio) is None


@pytest.mark.ac("AC-NORM-04")
def test_remitente_no_se_enmascara(fabrica_eml: Callable[..., bytes]) -> None:
    """El remitente (From) NO se enmascara (excepción FR-005)."""
    eml = fabrica_eml(remitente="remitente.puro@empresa.com")
    normalizado = normalizar_desde_eml(eml)
    vista = enmascarar_para_terceros(normalizado)

    from_hdr = [c.valor for c in vista.cabeceras if c.nombre.lower() == "from"]
    assert any("remitente.puro@empresa.com" in v for v in from_hdr)


@pytest.mark.ac("AC-NORM-04")
def test_lo_persistido_sin_correos_ni_digitos(fabrica_eml: Callable[..., bytes]) -> None:
    """Lo que se persiste (model_dump enmascarado) no contiene otros correos ni dígitos largos."""
    eml = fabrica_eml(
        html="<p>juan.perez@empresa.com 4111111111111111</p>",
        texto="juan.perez@empresa.com 4111111111111111",
        destinatario="destino@empresa.com",
        asunto="factura para ana.garcia@otro.co",
    )
    normalizado = normalizar_desde_eml(eml)
    vista = enmascarar_para_terceros(normalizado)
    persistible = json.dumps(vista.model_dump(exclude={"cabeceras"}), ensure_ascii=False)

    # Fuera el HTML (nunca persistido); los campos de texto quedan enmascarados.
    assert "juan.perez@empresa.com" not in persistible
    assert "ana.garcia@otro.co" not in persistible
    assert CONTIENE_DIGITOS_LARGOS.search(persistible) is None


# --- Propiedades con hypothesis (la spec pide pruebas basadas en propiedades) ---


@settings(max_examples=60, deadline=None)
@given(st.text(min_size=0, max_size=40))
def test_propiedad_correos_enmascarados(relleno: str) -> None:
    """Cualquier correo generado queda enmascarado con la forma `x***@dominio`."""
    local, dominio = "juan.perez", "empresa.com"
    correo = f"{local}@{dominio}"
    salida = enmascarar_texto(f"{relleno} {correo} {relleno}")
    assert correo not in salida
    assert f"{local[0]}***@{dominio}" in salida
    assert CONTIENE_CORREO.search(salida.replace(f"{local[0]}***@{dominio}", "")) is None


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=13, max_value=32))
def test_propiedad_digitos_largos_enmascarados(n: int) -> None:
    """Cualquier secuencia de 13 a 32 dígitos queda totalmente oculta (sin residuo >=13)."""
    digitos = "4" * n
    salida = enmascarar_texto(f"ref {digitos} ref")
    assert digitos not in salida
    assert CONTIENE_DIGITOS_LARGOS.search(salida) is None


@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=1, max_value=12))
def test_propiedad_digitos_cortos_intactos(n: int) -> None:
    """Secuencias de menos de 13 dígitos NO se tocan (valor límite inferior)."""
    digitos = "7" * n
    salida = enmascarar_texto(f"ref {digitos} ref")
    assert digitos in salida


@settings(max_examples=30, deadline=None)
@given(st.text(min_size=0, max_size=60))
def test_propiedad_enmascarado_idempotente(texto: str) -> None:
    """Enmascarar dos veces es igual que enmascarar una vez."""
    una_vez = enmascarar_texto(texto)
    assert enmascarar_texto(una_vez) == una_vez


@pytest.mark.ac("AC-NORM-04")
def test_vista_llm_acota_asunto_html_y_cabeceras() -> None:
    """La vista enviada al modelo acota asunto, HTML y cabeceras a sus topes (Art. 0.6)."""
    email = EmailData(
        subject="A" * (LIMITE_ASUNTO_LLM * 3),
        htmlBody="<p>" + "B" * (LIMITE_HTML_LLM * 3) + "</p>",
        headers="X-Gigante: " + "C" * (LIMITE_HEADERS_LLM * 3),
    )
    vista = enmascarar_para_terceros(email)
    assert len(vista.subject) == LIMITE_ASUNTO_LLM
    assert len(vista.htmlBody) == LIMITE_HTML_LLM
    assert len(vista.headers) == LIMITE_HEADERS_LLM


@pytest.mark.ac("AC-NORM-04")
def test_vista_llm_respeta_presupuesto_total() -> None:
    """El texto total que ve el modelo (asunto+HTML+cabeceras) no excede 20 000 (FR-004)."""
    email = EmailData(
        subject="A" * (LIMITE_ASUNTO_LLM * 3),
        htmlBody="<p>" + "B" * (LIMITE_HTML_LLM * 3) + "</p>",
        headers="X-Gigante: " + "C" * (LIMITE_HEADERS_LLM * 3),
    )
    vista = enmascarar_para_terceros(email)
    total = len(vista.subject) + len(vista.htmlBody) + len(vista.headers)
    assert total <= LIMITE_CARACTERES_TEXTO


@pytest.mark.ac("AC-NORM-04")
def test_vista_llm_no_trunca_contenido_corto() -> None:
    """Un correo dentro de los topes conserva asunto, HTML y cabeceras intactos."""
    email = EmailData(
        subject="Asunto corto",
        htmlBody="<p>hola</p>",
        headers="X-Mailer: mi-cliente\nX-Priority: 1",
    )
    vista = enmascarar_para_terceros(email)
    assert vista.subject == "Asunto corto"
    assert vista.htmlBody == "<p>hola</p>"
    assert vista.headers == "X-Mailer: mi-cliente\nX-Priority: 1"
