"""Tests de integración: veredicto fluye desde el pipeline hasta el ejecutor de acciones.

Verifica que:
1. PhishingReport.veredicto se propaga correctamente desde cada ruta del pipeline
2. El ejecutor de acciones recibe el veredicto correcto
3. La tabla veredicto→acciones se aplica correctamente desde el poller
"""

from __future__ import annotations

from src.level2_agent.models import PhishingReport


class TestVeredictoEnReporte:
    """Tests de que el veredicto se propaga en PhishingReport."""

    def test_benign_report_tiene_veredicto_sin_indicadores(self) -> None:
        """generate_benign_report → veredicto="sin_indicadores"."""
        from src.level2_agent.agent import generate_benign_report

        report = generate_benign_report(10.0)
        assert report.veredicto == "sin_indicadores"
        assert report.es_phishing is False

    def test_malicious_report_tiene_veredicto_malicioso(self) -> None:
        """generate_malicious_report → veredicto="malicioso"."""
        from src.level2_agent.agent import generate_malicious_report

        report = generate_malicious_report(80.0, [{"caracteristica": "test"}])
        assert report.veredicto == "malicioso"
        assert report.es_phishing is True

    def test_veredicto_a_report_malicioso(self) -> None:
        """_veredicto_a_report("malicioso") → veredicto="malicioso"."""
        from src.level2_agent.agent import _veredicto_a_report

        report = _veredicto_a_report("malicioso", 80.0, [{"caracteristica": "x"}], None)
        assert report.veredicto == "malicioso"
        assert report.es_phishing is True

    def test_veredicto_a_report_sospechoso(self) -> None:
        """_veredicto_a_report("sospechoso") → veredicto="sospechoso"."""
        from src.level2_agent.agent import _veredicto_a_report

        report = _veredicto_a_report("sospechoso", 50.0, [{"caracteristica": "x"}], None)
        assert report.veredicto == "sospechoso"
        assert report.es_phishing is True

    def test_veredicto_a_report_revision_manual(self) -> None:
        """_veredicto_a_report("revision_manual") → veredicto="revision_manual"."""
        from src.level2_agent.agent import _veredicto_a_report

        report = _veredicto_a_report("revision_manual", 50.0, [{"caracteristica": "x"}], None)
        assert report.veredicto == "revision_manual"
        assert report.es_phishing is True

    def test_veredicto_a_report_sin_indicadores(self) -> None:
        """_veredicto_a_report("sin_indicadores") → veredicto="sin_indicadores"."""
        from src.level2_agent.agent import _veredicto_a_report

        report = _veredicto_a_report("sin_indicadores", 10.0, [], None)
        assert report.veredicto == "sin_indicadores"
        assert report.es_phishing is False


class TestVeredictoAEjecutor:
    """Tests de que el veredicto del reporte alimenta correctamente el ejecutor."""

    def test_malicioso_genera_acciones_completas(self) -> None:
        """veredicto="malicioso" → etiquetar + archivar + ticket."""
        from src.level2_agent.acciones import Accion, resolver_acciones

        acciones = resolver_acciones("malicioso")
        assert Accion.ETIQUETAR_PHISHING in acciones
        assert Accion.ARCHIVAR in acciones
        assert Accion.CREAR_TICKET in acciones

    def test_sospechoso_genera_etiquetar_y_ticket_baja(self) -> None:
        """veredicto="sospechoso" → etiquetar revisar + ticket baja."""
        from src.level2_agent.acciones import Accion, resolver_acciones

        acciones = resolver_acciones("sospechoso")
        assert Accion.ETIQUETAR_REVISAR in acciones
        assert Accion.CREAR_TICKET_BAJA in acciones

    def test_revision_manual_genera_etiquetar_y_ticket_baja(self) -> None:
        """veredicto="revision_manual" → etiquetar revisar + ticket baja."""
        from src.level2_agent.acciones import Accion, resolver_acciones

        acciones = resolver_acciones("revision_manual")
        assert Accion.ETIQUETAR_REVISAR in acciones
        assert Accion.CREAR_TICKET_BAJA in acciones

    def test_sin_indicadores_solo_marca_leido(self) -> None:
        """veredicto="sin_indicadores" → solo marcar leído."""
        from src.level2_agent.acciones import Accion, resolver_acciones

        acciones = resolver_acciones("sin_indicadores")
        assert acciones == [Accion.MARCAR_LEIDO]


class TestEntradaAccionesDesdeReporte:
    """Tests de construcción de EntradaAcciones desde un PhishingReport."""

    def test_construir_entrada_desde_reporte(self) -> None:
        """Se puede construir EntradaAcciones desde un PhishingReport con veredicto."""
        from src.level2_agent.acciones import EntradaAcciones

        report = PhishingReport(
            resumen="Test",
            analisis_tecnico="Test tech",
            indicadores_phishing=["test"],
            es_phishing=True,
            nivel_severidad="Alto",
            justificacion_veredicto="Test just",
            veredicto="malicioso",
        )

        entrada = EntradaAcciones(
            veredicto=report.veredicto,  # type: ignore[arg-type]
            nivel_severidad=report.nivel_severidad,  # type: ignore[arg-type]
            message_id="msg123",
            remitente="test@example.com",
            asunto="Test subject",
            urls=["https://evil.com"],
            reporte=report,
            origen="gmail",
        )

        assert entrada.veredicto == "malicioso"
        assert entrada.message_id == "msg123"
        assert entrada.origen == "gmail"
