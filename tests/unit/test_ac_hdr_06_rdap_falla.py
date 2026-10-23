"""AC-HDR-06: si RDAP no responde -> DOMINIO_EDAD_DESCONOCIDA (0 puntos), sin excepcion."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.motor import evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.ac("AC-HDR-06")
def test_rdap_falla_sin_excepcion(construir_correo: Any, rdap_nulo: Any) -> None:
    config = ConfigBanderas(authserv_id="mio.com")
    correo = construir_correo(cabeceras=[("From", "ana@dominio-desconocido.com")])
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)  # no lanza
    banderas = {b.codigo: b for b in r.banderas}
    assert "DOMINIO_EDAD_DESCONOCIDA" in banderas
    assert banderas["DOMINIO_EDAD_DESCONOCIDA"].puntos == 0
    assert banderas["DOMINIO_EDAD_DESCONOCIDA"].severidad == "informativa"
    assert "DOMINIO_NUEVO" not in banderas  # sin fecha no se infiere antigüedad
