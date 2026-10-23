"""AC-HDR-03: sin Authentication-Results la autenticación queda en `desconocido` (nunca `pass`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from src.level2_agent.banderas.configuracion import ConfigBanderas
from src.level2_agent.banderas.motor import evaluar_banderas

AHORA = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.ac("AC-HDR-03")
def test_sin_cabecera_auth_results(construir_correo: Any, rdap_nulo: Any) -> None:
    config = ConfigBanderas(authserv_id="mail.empresa.com")
    correo = construir_correo(cabeceras=[("From", "ana@empresa.com")])
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    est = r.estados_autenticacion
    assert (est.spf, est.dkim, est.dmarc) == ("desconocido", "desconocido", "desconocido")
    assert est.spf != "pass"  # jamas se infiere pass
    codigos = {b.codigo for b in r.banderas}
    assert "AUTH_NO_EVALUABLE" in codigos
    # al no ser evaluable, tampoco se declaran fallos
    assert "SPF_FALLA" not in codigos
    assert "DKIM_FALLA" not in codigos
    assert "DMARC_FALLA" not in codigos


@pytest.mark.ac("AC-HDR-03")
def test_auth_confiable_no_dispara_auth_no_evaluable(construir_correo: Any, rdap_nulo: Any) -> None:
    """Si hay AR propio confiable, AUTH_NO_EVALUABLE no se activa aunque un método falte."""
    config = ConfigBanderas(authserv_id="mail.empresa.com")
    correo = construir_correo(
        cabeceras=[
            ("From", "ana@empresa.com"),
            ("Authentication-Results", "mail.empresa.com; spf=pass"),
        ]
    )
    r = evaluar_banderas(correo, config=config, ahora=AHORA, cliente_rdap=rdap_nulo)
    assert "AUTH_NO_EVALUABLE" not in {b.codigo for b in r.banderas}
    assert r.estados_autenticacion.spf == "pass"
    assert r.estados_autenticacion.dkim == "desconocido"  # método ausente, no inferido
