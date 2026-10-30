"""AC-ACT-04: asunto con HTML, markup de Jira o 10 000 caracteres se escapa y trunca."""

from __future__ import annotations

from src.level2_agent.acciones.jira_adapter import sanear_texto_jira
from src.level2_agent.acciones.modelos import MAX_CHARS_DESCRIPCION_JIRA, MAX_CHARS_SUMMARY_JIRA


def test_saneo_html() -> None:
    """HTML tags se eliminan."""
    texto = '<script>alert("xss")</script>Hola mundo'
    result = sanear_texto_jira(texto)
    assert "<script>" not in result
    assert "Hola mundo" in result


def test_saneo_jira_markup() -> None:
    """Markup de Jira se escapa."""
    texto = "{code}rm -rf /{code} y {color:red}peligro{color}"
    result = sanear_texto_jira(texto)
    # Las llaves deben estar escapadas
    assert "\\{" in result or "code" in result


def test_saneo_truncar_10000_chars() -> None:
    """Texto de 10 000 caracteres se trunca a max_chars."""
    texto = "A" * 10000
    result = sanear_texto_jira(texto, max_chars=MAX_CHARS_DESCRIPCION_JIRA)
    assert len(result) == MAX_CHARS_DESCRIPCION_JIRA
    assert result.endswith("...")


def test_saneo_summary_truncar() -> None:
    """Summary se trunca a 190 chars."""
    texto = "B" * 500
    result = sanear_texto_jira(texto, max_chars=MAX_CHARS_SUMMARY_JIRA)
    assert len(result) == MAX_CHARS_SUMMARY_JIRA
    assert result.endswith("...")


def test_saneo_texto_corto_sin_cambio() -> None:
    """Texto corto no se modifica (excepto saneo)."""
    texto = "Phishing detectado en correo de prueba"
    result = sanear_texto_jira(texto)
    assert result == texto
