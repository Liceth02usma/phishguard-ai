"""Cobertura de la API `normalizar_desde_api` y de los guardas de tipo (contrato público).

Complementa los AC-NORM-01..06 con la ruta de la futura API (spec 12) y con las
excepciones `TypeError` documentadas en el contrato, para elevar la cobertura del
orquestador y fijar la conducta de los guardas.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

import pytest
from src.level2_agent.normalizacion import (
    BANDERA_ENTRADA_DEGRADADA,
    normalizar_desde_api,
    normalizar_desde_eml,
    normalizar_desde_gmail,
)


def test_api_desde_raw_base64(fabrica_eml: Callable[..., bytes]) -> None:
    """Un payload con `raw` (Base64) recorre el camino MIME y marca `origen="api"`."""
    eml = fabrica_eml(texto="hola", asunto="factura")
    raw_b64 = base64.urlsafe_b64encode(eml).decode("ASCII")
    resultado = normalizar_desde_api({"raw": raw_b64})
    assert resultado.origen == "api"
    assert resultado.subject == "factura"
    assert "hola" in resultado.texto_limpio


def test_api_desde_campos() -> None:
    """Sin `raw`, construye el correo desde los campos del payload."""
    resultado = normalizar_desde_api(
        {
            "subject": "asunto api",
            "from": "remitente@empresa.com",
            "to": "destino@empresa.com",
            "text": "cuerpo del texto",
        }
    )
    assert resultado.origen == "api"
    assert resultado.subject == "asunto api"
    assert resultado.recipient == "destino@empresa.com"
    assert "cuerpo del texto" in resultado.texto_limpio
    assert BANDERA_ENTRADA_DEGRADADA not in resultado.banderas


def test_api_raw_base64_invalido_degrada() -> None:
    """Un `raw` que no es Base64 válido no lanza; degrada y marca revisión manual."""
    resultado = normalizar_desde_api({"raw": "!!!no-base64!!!"})
    assert resultado.revision_manual is True


def test_api_payload_vacio_degrada() -> None:
    """Un payload sin ningún campo útil degrada con `ENTRADA_DEGRADADA`."""
    resultado = normalizar_desde_api({})
    assert BANDERA_ENTRADA_DEGRADADA in resultado.banderas
    assert resultado.revision_manual is True


def test_api_payload_no_dict_lanza() -> None:
    """Un payload que no es dict lanza `TypeError` (documentado en el contrato)."""
    with pytest.raises(TypeError):
        normalizar_desde_api("no soy un dict")  # type: ignore[arg-type]


def test_gmail_raw_no_bytes_lanza() -> None:
    """`normalizar_desde_gmail` lanza `TypeError` si `raw_bytes` no es bytes."""
    with pytest.raises(TypeError):
        normalizar_desde_gmail("no bytes", "id-1")  # type: ignore[arg-type]


def test_eml_contenido_no_bytes_lanza() -> None:
    """`normalizar_desde_eml` lanza `TypeError` si `contenido` no es bytes."""
    with pytest.raises(TypeError):
        normalizar_desde_eml("no bytes")  # type: ignore[arg-type]


def test_eml_sin_message_id_es_determinista() -> None:
    """Un `.eml` sin cabecera `Message-ID` genera un ID determinista (sha256[:16])."""
    eml = b"From: a@b.com\r\nSubject: x\r\n\r\nhola\r\n"
    uno = normalizar_desde_eml(eml)
    dos = normalizar_desde_eml(eml)
    assert len(uno.message_id) == 16
    assert uno.message_id == dos.message_id


def test_eml_con_message_id_usa_cabecera() -> None:
    """Un `.eml` con cabecera `Message-ID` la conserva como `message_id`."""
    eml = b"From: a@b.com\r\nMessage-ID: <abc@x.com>\r\n\r\nhola\r\n"
    resultado = normalizar_desde_eml(eml)
    assert resultado.message_id == "<abc@x.com>"


def test_gmail_origen_y_id() -> None:
    """`normalizar_desde_gmail` marca `origen="gmail"` y respeta el `message_id` dado."""
    eml = b"From: a@b.com\r\nSubject: s\r\n\r\nhola\r\n"
    resultado = normalizar_desde_gmail(eml, "gid-9")
    assert resultado.origen == "gmail"
    assert resultado.message_id == "gid-9"


def test_api_determinismo_raw() -> None:
    """El mismo `raw` produce el mismo `message_id` (determinismo, Art. II.5)."""
    eml = b"From: a@b.com\r\nSubject: x\r\n\r\nhola\r\n"
    raw_b64 = base64.urlsafe_b64encode(eml).decode("ASCII")
    uno: Any = normalizar_desde_api({"raw": raw_b64})
    dos: Any = normalizar_desde_api({"raw": raw_b64})
    assert uno.message_id == dos.message_id
