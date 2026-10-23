"""Pruebas unitarias del parser RFC 8601 de Authentication-Results (research D4).

Tabla de decisión (Art. II.2, obligatoria): authserv-id coincide/no × método
presente/ausente × resultado. Cubre los estados y `hay_confiable`.
"""

from __future__ import annotations

from src.level2_agent.banderas.autenticacion import calcular_autenticacion
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.models import Cabecera, EmailData

_AUTH = "mail.empresa.com"


def _correo(*ars: str) -> EmailData:
    return EmailData(
        cabeceras=[Cabecera(nombre="Authentication-Results", valor=a) for a in ars]
    )


def test_authserv_id_coincide_fija_estados() -> None:
    cfg = ConfigBanderas(authserv_id=_AUTH)
    ra = calcular_autenticacion(cfg, _correo(f"{_AUTH}; spf=pass dkim=pass dmarc=fail").cabeceras)
    assert ra.hay_confiable is True
    assert ra.estados.spf == "pass"
    assert ra.estados.dkim == "pass"
    assert ra.estados.dmarc == "fail"


def test_authserv_id_distinto_no_confia() -> None:
    cfg = ConfigBanderas(authserv_id=_AUTH)
    ra = calcular_autenticacion(cfg, _correo("otro.mx; spf=pass").cabeceras)
    assert ra.hay_confiable is False
    assert ra.estados.spf == "desconocido"


def test_metodos_separados_por_punto_y_coma() -> None:
    cfg = ConfigBanderas(authserv_id="mio.com")
    ra = calcular_autenticacion(cfg, _correo("mio.com; spf=softfail; dkim=permerror").cabeceras)
    assert ra.estados.spf == "softfail"
    assert ra.estados.dkim == "permerror"


def test_primer_confiable_gana() -> None:
    cfg = ConfigBanderas(authserv_id="mio.com")
    ra = calcular_autenticacion(
        cfg, _correo("mio.com; spf=pass", "mio.com; spf=fail").cabeceras
    )
    assert ra.estados.spf == "pass"  # el primero en orden fisico gana


def test_comentarios_en_authserv_id() -> None:
    cfg = ConfigBanderas(authserv_id="mio.com")
    ra = calcular_autenticacion(cfg, _correo("mio.com (boundary); spf=pass").cabeceras)
    assert ra.hay_confiable is True
    assert ra.estados.spf == "pass"


def test_metodo_ausente_en_confiable_es_desconocido() -> None:
    cfg = ConfigBanderas(authserv_id="mio.com")
    ra = calcular_autenticacion(cfg, _correo("mio.com; spf=pass").cabeceras)
    assert ra.hay_confiable is True  # hay cabecera confiable
    assert ra.estados.dkim == "desconocido"  # pero el metodo no viene evaluado


def test_sin_cabeceras() -> None:
    cfg = ConfigBanderas(authserv_id="mio.com")
    ra = calcular_autenticacion(cfg, [])
    assert ra.hay_confiable is False
    assert (ra.estados.spf, ra.estados.dkim, ra.estados.dmarc) == ("desconocido",) * 3
