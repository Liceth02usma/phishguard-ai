"""Tests del módulo de screenshots HCTI (spec 010, D12).

- generar_screenshot con credenciales válidas (mock)
- generar_screenshot sin credenciales → None
- generar_screenshot con HTML vacío → None
- generar_screenshot con error HTTP → None (degradación graceful)
- generar_screenshot con timeout → None
- EntradaAcciones con html_body
- Integración: ejecutor genera screenshot al crear ticket
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.level2_agent.acciones.modelos import EntradaAcciones
from src.level2_agent.models import PhishingReport


# --- HCTI adapter tests ---


class TestGenerarScreenshot:
    """Tests de generar_screenshot (HCTI adapter)."""

    def test_html_vacio_retorna_none(self) -> None:
        """HTML vacío → None."""
        from src.level2_agent.screenshots import generar_screenshot

        assert generar_screenshot("") is None

    def test_html_solo_espacios_retorna_none(self) -> None:
        """HTML con solo espacios → None."""
        from src.level2_agent.screenshots import generar_screenshot

        assert generar_screenshot("   ") is None

    def test_sin_credenciales_retorna_none(self) -> None:
        """Sin HCTI_API_ID/HCTI_API_KEY → None."""
        from src.level2_agent.screenshots import generar_screenshot

        os.environ.pop("HCTI_API_ID", None)
        os.environ.pop("HCTI_API_KEY", None)
        assert generar_screenshot("<html>test</html>") is None

    def test_sin_api_id_retorna_none(self) -> None:
        """Sin HCTI_API_ID → None."""
        from src.level2_agent.screenshots import generar_screenshot

        os.environ.pop("HCTI_API_ID", None)
        os.environ["HCTI_API_KEY"] = "test-key"
        try:
            assert generar_screenshot("<html>test</html>") is None
        finally:
            del os.environ["HCTI_API_KEY"]

    def test_con_credenciales_llama_api(self) -> None:
        """Con credenciales válidas, llama a la API y retorna URL."""
        from src.level2_agent.screenshots import generar_screenshot

        os.environ["HCTI_API_ID"] = "test-id"
        os.environ["HCTI_API_KEY"] = "test-key"
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "url": "https://hcti.io/v1/image/abc123.png"
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.post", return_value=mock_response) as mock_post:
                result = generar_screenshot("<html><body>Phish</body></html>")

            assert result == "https://hcti.io/v1/image/abc123.png"
            mock_post.assert_called_once()
            # Verificar auth
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs["auth"] == ("test-id", "test-key")
        finally:
            del os.environ["HCTI_API_ID"]
            del os.environ["HCTI_API_KEY"]

    def test_error_http_retorna_none(self) -> None:
        """Error HTTP (401, 500) → None (degradación graceful)."""
        import httpx

        from src.level2_agent.screenshots import generar_screenshot

        os.environ["HCTI_API_ID"] = "test-id"
        os.environ["HCTI_API_KEY"] = "test-key"
        try:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )

            with patch("httpx.post", return_value=mock_response):
                result = generar_screenshot("<html>test</html>")

            assert result is None
        finally:
            del os.environ["HCTI_API_ID"]
            del os.environ["HCTI_API_KEY"]

    def test_timeout_retorna_none(self) -> None:
        """Timeout → None (degradación graceful)."""
        import httpx

        from src.level2_agent.screenshots import generar_screenshot

        os.environ["HCTI_API_ID"] = "test-id"
        os.environ["HCTI_API_KEY"] = "test-key"
        try:
            with patch(
                "httpx.post",
                side_effect=httpx.TimeoutException("timeout"),
            ):
                result = generar_screenshot("<html>test</html>")

            assert result is None
        finally:
            del os.environ["HCTI_API_ID"]
            del os.environ["HCTI_API_KEY"]

    def test_respuesta_sin_url_retorna_none(self) -> None:
        """Respuesta sin campo url → None."""
        from src.level2_agent.screenshots import generar_screenshot

        os.environ["HCTI_API_ID"] = "test-id"
        os.environ["HCTI_API_KEY"] = "test-key"
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"error": "something"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.post", return_value=mock_response):
                result = generar_screenshot("<html>test</html>")

            assert result is None
        finally:
            del os.environ["HCTI_API_ID"]
            del os.environ["HCTI_API_KEY"]


# --- EntradaAcciones con html_body ---


class TestEntradaAccionesHtmlBody:
    """Tests de EntradaAcciones con html_body."""

    def test_html_body_no_se_persiste(self) -> None:
        """html_body es exclude=True — no aparece en model_dump."""
        report = PhishingReport(
            resumen="Test",
            analisis_tecnico="Tech",
            indicadores_phishing=[],
            es_phishing=True,
            nivel_severidad="Alto",
            justificacion_veredicto="Just",
            veredicto="malicioso",
        )
        entrada = EntradaAcciones(
            veredicto="malicioso",
            nivel_severidad="Alto",
            message_id="msg1",
            remitente="test@evil.com",
            asunto="Phish",
            reporte=report,
            origen="gmail",
            html_body="<html><body>Phish</body></html>",
        )

        assert entrada.html_body == "<html><body>Phish</body></html>"
        # html_body no debe estar en model_dump (exclude=True)
        dump = entrada.model_dump()
        assert "html_body" not in dump

    def test_html_body_default_vacio(self) -> None:
        """html_body default es vacío."""
        report = PhishingReport(
            resumen="Test",
            analisis_tecnico="Tech",
            indicadores_phishing=[],
            es_phishing=False,
            nivel_severidad="Bajo",
            justificacion_veredicto="Just",
        )
        entrada = EntradaAcciones(
            veredicto="sin_indicadores",
            nivel_severidad="Bajo",
            message_id="msg1",
            remitente="test@good.com",
            asunto="Safe",
            reporte=report,
            origen="gmail",
        )

        assert entrada.html_body == ""


# --- Integración: ejecutor con screenshot ---


class TestEjecutorConScreenshot:
    """Tests de integración del ejecutor con generación de screenshot."""

    def test_ticket_malicioso_con_screenshot(self) -> None:
        """Ticket malicioso con html_body → descripción incluye screenshot URL."""
        from datetime import datetime, timezone

        from src.level2_agent.acciones import (
            EntradaAcciones,
            ejecutar_acciones,
        )
        from src.level2_agent.acciones.gmail_adapter import GmailAdapter
        from src.level2_agent.acciones.jira_adapter import JiraAdapter, ResultadoJira

        report = PhishingReport(
            resumen="Phishing detectado",
            analisis_tecnico="SPF fail, DKIM fail",
            indicadores_phishing=["spf_fail"],
            es_phishing=True,
            nivel_severidad="Alto",
            justificacion_veredicto="Just",
            veredicto="malicioso",
        )
        entrada = EntradaAcciones(
            veredicto="malicioso",
            nivel_severidad="Alto",
            message_id="msg_screenshot_1",
            remitente="phish@evil.com",
            asunto="Urgente",
            reporte=report,
            origen="gmail",
            html_body="<html><body>Click here</body></html>",
        )

        # Mock de screenshot
        with patch(
            "src.level2_agent.screenshots.hcti_adapter.httpx.post"
        ) as mock_post:
            os.environ["HCTI_API_ID"] = "test-id"
            os.environ["HCTI_API_KEY"] = "test-key"
            os.environ["ACCIONES_DRY_RUN"] = "false"

            try:
                # Mock screenshot response
                mock_ss_response = MagicMock()
                mock_ss_response.status_code = 200
                mock_ss_response.json.return_value = {
                    "url": "https://hcti.io/v1/image/test.png"
                }
                mock_ss_response.raise_for_status = MagicMock()
                mock_post.return_value = mock_ss_response

                # Mock adapters
                gmail_mock = MagicMock(spec=GmailAdapter)
                jira_mock = MagicMock(spec=JiraAdapter)
                jira_mock.buscar_por_huella.return_value = None
                jira_mock.crear_ticket.return_value = ResultadoJira(
                    exito=True, issue_key="SCRUM-123"
                )

                resultado = ejecutar_acciones(
                    entrada,
                    gmail=gmail_mock,
                    jira=jira_mock,
                    ahora=datetime.now(tz=timezone.utc),
                )

                # Verificar que se creó el ticket
                assert resultado.ticket_key == "SCRUM-123"

                # Verificar que la descripción incluye el screenshot
                call_args = jira_mock.crear_ticket.call_args
                campos = call_args[0][0]
                descripcion = campos["fields"]["description"]
                assert "📸" in descripcion
                assert "https://hcti.io/v1/image/test.png" in descripcion

            finally:
                os.environ.pop("HCTI_API_ID", None)
                os.environ.pop("HCTI_API_KEY", None)
                os.environ.pop("ACCIONES_DRY_RUN", None)

    def test_ticket_sin_html_body_sin_screenshot(self) -> None:
        """Ticket sin html_body → descripción sin screenshot."""
        from datetime import datetime, timezone

        from src.level2_agent.acciones import (
            EntradaAcciones,
            ejecutar_acciones,
        )
        from src.level2_agent.acciones.gmail_adapter import GmailAdapter
        from src.level2_agent.acciones.jira_adapter import JiraAdapter, ResultadoJira

        report = PhishingReport(
            resumen="Phishing detectado",
            analisis_tecnico="SPF fail",
            indicadores_phishing=["spf_fail"],
            es_phishing=True,
            nivel_severidad="Alto",
            justificacion_veredicto="Just",
            veredicto="malicioso",
        )
        entrada = EntradaAcciones(
            veredicto="malicioso",
            nivel_severidad="Alto",
            message_id="msg_no_html_1",
            remitente="phish@evil.com",
            asunto="Urgente",
            reporte=report,
            origen="gmail",
            html_body="",  # Sin HTML
        )

        os.environ["ACCIONES_DRY_RUN"] = "false"
        os.environ.pop("HCTI_API_ID", None)
        os.environ.pop("HCTI_API_KEY", None)

        try:
            gmail_mock = MagicMock(spec=GmailAdapter)
            jira_mock = MagicMock(spec=JiraAdapter)
            jira_mock.buscar_por_huella.return_value = None
            jira_mock.crear_ticket.return_value = ResultadoJira(
                exito=True, issue_key="SCRUM-456"
            )

            resultado = ejecutar_acciones(
                entrada,
                gmail=gmail_mock,
                jira=jira_mock,
                ahora=datetime.now(tz=timezone.utc),
            )

            # Verificar que se creó el ticket
            assert resultado.ticket_key == "SCRUM-456"

            # Verificar que la descripción NO incluye screenshot
            call_args = jira_mock.crear_ticket.call_args
            campos = call_args[0][0]
            descripcion = campos["fields"]["description"]
            assert "📸" not in descripcion

        finally:
            os.environ.pop("ACCIONES_DRY_RUN", None)
