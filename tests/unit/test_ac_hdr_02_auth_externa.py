"""AC-HDR-02: un Authentication-Results de servidor externo no altera SPF/DKIM/DMARC."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.motor import evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.ac("AC-HDR-02")
def test_auth_externa_ignorada(construir_correo: Any, rdap_nulo: Any) -> None:
    # El authserv-id configurado es el propio; la cabecera viene de un externo.
    config = ConfigBanderas(authserv_id="mail.empresa.com")
    correo = construir_correo(
        cabeceras=[
            ("From", "ana@empresa.com"),
            ("Authentication-Results", "mx.externo.net; spf=pass dkim=pass dmarc=pass"),
        ]
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    est = r.estados_autenticacion
    assert est.spf == "desconocido"
    assert est.dkim == "desconocido"
    assert est.dmarc == "desconocido"
    codigos = {b.codigo for b in r.banderas}
    assert "AUTH_NO_EVALUABLE" in codigos  # no hay AR de confianza
    assert "SPF_FALLA" not in codigos
