"""AC-HDR-04: paypa1.com vs paypal.com activa DOMINIO_PARECIDO; empresa.com.co vs empresa.com no."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.motor import evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.ac("AC-HDR-04")
def test_paypa1_es_parecido_a_paypal(construir_correo: Any, rdap_nulo: Any) -> None:
    config = ConfigBanderas(authserv_id="mio.com", marcas_protegidas=["paypal.com"])
    correo = construir_correo(cabeceras=[("From", "cliente@paypa1.com")])
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    assert any(b.codigo == "DOMINIO_PARECIDO" for b in r.banderas)


@pytest.mark.ac("AC-HDR-04")
def test_empresa_com_co_no_confunde_con_empresa_com(construir_correo: Any, rdap_nulo: Any) -> None:
    config = ConfigBanderas(authserv_id="mio.com", marcas_protegidas=["empresa.com"])
    correo = construir_correo(cabeceras=[("From", "ana@empresa.com.co")])
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    assert not any(b.codigo == "DOMINIO_PARECIDO" for b in r.banderas)
