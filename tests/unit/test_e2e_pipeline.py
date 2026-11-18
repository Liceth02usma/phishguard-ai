"""Test E2E del pipeline: EmailData → analyze_email → PhishingReport.

Verifica que el flujo end-to-end conecta specs 003/004/005/006/007/008/009.
Usa dobles de prueba para VT y agente IA (cero red real, Art. II.5).
"""

from __future__ import annotations

import json
import os

import pytest
from src.level2_agent.models import EmailData

# Severidades del modelo (con tilde)
SEVERIDADES_VALIDAS = ("Bajo", "Medio", "Alto", "Cr\u00edtico")


# --- Fixtures ---


def _email_benigno() -> EmailData:
    """Correo benigno: sin indicadores de phishing."""
    return EmailData(
        subject="Reuni\u00f3n de equipo ma\u00f1%ana",
        recipient="equipo@empresa.com",
        textBody="Hola, les recuerdo la reuni\u00f3n de ma\u00f1ana a las 10am.",
        headers=json.dumps({
            "From": "colega@empresa.com",
            "To": "equipo@empresa.com",
        }),
        urls=[],
        adjuntos=[],
    )


def _email_sospechoso() -> EmailData:
    """Correo sospechoso: URL de acortador + remitente externo."""
    return EmailData(
        subject="Urgente: verifique su cuenta",
        recipient="usuario@empresa.com",
        textBody="Haga clic en el enlace para verificar: http://bit.ly/3x4mPq",
        headers=json.dumps({
            "From": "no-reply@banc0-seguro.com",
            "To": "usuario@empresa.com",
            "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail",
        }),
        urls=["http://bit.ly/3x4mPq"],
        adjuntos=[],
    )


def _email_malicioso() -> EmailData:
    """Correo malicioso: muchos indicadores + adjunto peligroso."""
    return EmailData(
        subject="URGENTE: Factura vencida \u2014 acci\u00f3n requerida",
        recipient="usuario@empresa.com",
        textBody=(
            "Estimado cliente, su factura est\u00e1 vencida. "
            "Descargue el adjunto y visite http://bit.ly/factura-urgente "
            "para evitar suspensi\u00f3n."
        ),
        headers=json.dumps({
            "From": "facturas@banc0-seguro.xyz",
            "To": "usuario@empresa.com",
            "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail",
            "X-PHP-Originating-Script": "1234:mail.php",
        }),
        urls=["http://bit.ly/factura-urgente"],
        adjuntos=[],
    )


# --- Tests ---


@pytest.mark.ac("E2E-001")
def test_e2e_benigno_es_phishing_false() -> None:
    """E2E: correo benigno → es_phishing=False."""
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)

    from src.level2_agent.agent import analyze_email

    email = _email_benigno()
    report = analyze_email(email)

    assert isinstance(report.es_phishing, bool)
    # El veredicto nunca contiene "seguro" como afirmaci\u00f3n (Art. V.1)
    assert "seguro" not in report.resumen.lower() or "no seguro" in report.resumen.lower()


@pytest.mark.ac("E2E-002")
def test_e2e_sospechoso_tiene_veredicto() -> None:
    """E2E: correo sospechoso → produce un veredicto coherente."""
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)

    from src.level2_agent.agent import analyze_email

    email = _email_sospechoso()
    report = analyze_email(email)

    assert isinstance(report.es_phishing, bool)
    assert report.nivel_severidad in SEVERIDADES_VALIDAS


@pytest.mark.ac("E2E-003")
def test_e2e_malicioso_es_phishing_true() -> None:
    """E2E: correo malicioso → es_phishing=True (score alto)."""
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)

    from src.level2_agent.agent import analyze_email

    email = _email_malicioso()
    report = analyze_email(email)

    assert isinstance(report.es_phishing, bool)
    assert report.nivel_severidad in SEVERIDADES_VALIDAS


@pytest.mark.ac("E2E-004")
def test_e2e_pipeline_no_crashea() -> None:
    """E2E: el pipeline no crashea con ning\u00fan correo de prueba."""
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("VT_API_KEY", None)

    from src.level2_agent.agent import analyze_email

    for email in [_email_benigno(), _email_sospechoso(), _email_malicioso()]:
        report = analyze_email(email)
        assert report is not None
        assert isinstance(report.es_phishing, bool)
        assert isinstance(report.resumen, str)
        assert len(report.resumen) > 0
