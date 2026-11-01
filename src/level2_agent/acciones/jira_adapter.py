"""Adapter de Jira y saneo de texto para tickets (spec 010, M08, D2/D11).

JiraAdapter Protocol define la interfaz.
JiraReal envuelve jira_integration.py.
sanear_texto_jira escapa HTML, markup Jira y trunca (AC-ACT-04).
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from .modelos import MAX_CHARS_DESCRIPCION_JIRA, MAX_CHARS_SUMMARY_JIRA, ResultadoJira


class JiraAdapter(Protocol):
    """Protocol para el adapter de Jira (D2)."""

    def crear_ticket(self, campos: dict[str, Any]) -> ResultadoJira:
        """Crea un ticket. Retorna issue_key o error."""
        ...

    def buscar_por_huella(self, huella: str) -> str | None:
        """Busca ticket existente por huella de campaña. Retorna issue_key o None."""
        ...

    def vincular(self, key_origen: str, key_destino: str) -> None:
        """Vincula dos tickets (issue links)."""
        ...


class JiraReal:
    """Adapter real que envuelve jira_integration.py.

    Requiere JIRA_INSTANCE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN.
    """

    def crear_ticket(self, campos: dict[str, Any]) -> ResultadoJira:
        """Crea un ticket vía la API de Jira."""
        import os

        url = os.environ.get("JIRA_INSTANCE_URL", "")
        email = os.environ.get("JIRA_USER_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")

        if not all([url, email, token]):
            return ResultadoJira(
                exito=False, error="Credenciales Jira no configuradas"
            )

        try:
            import requests

            auth = (email, token)
            response = requests.post(
                f"{url.rstrip('/')}/rest/api/2/issue",
                json=campos,
                auth=auth,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            issue_key = data.get("key", "")
            return ResultadoJira(
                exito=True,
                issue_key=issue_key,
                url=f"{url}/browse/{issue_key}",
            )
        except Exception as e:
            return ResultadoJira(exito=False, error=str(e))

    def buscar_por_huella(self, huella: str) -> str | None:
        """Busca ticket existente por custom field huella_campaña."""
        import os

        url = os.environ.get("JIRA_INSTANCE_URL", "")
        email = os.environ.get("JIRA_USER_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")

        if not all([url, email, token]):
            return None

        try:
            import requests

            jql = f'cf[huella_campaña] = "{huella}"'
            auth = (email, token)
            response = requests.get(
                f"{url.rstrip('/')}/rest/api/2/search",
                params={"jql": jql, "maxResults": 1},
                auth=auth,
                timeout=15,
            )
            response.raise_for_status()
            issues = response.json().get("issues", [])
            if issues:
                return str(issues[0]["key"])
            return None
        except Exception:
            return None

    def vincular(self, key_origen: str, key_destino: str) -> None:
        """Vincula dos tickets con issue link."""
        import os

        url = os.environ.get("JIRA_INSTANCE_URL", "")
        email = os.environ.get("JIRA_USER_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")

        if not all([url, email, token]):
            return

        try:
            import requests

            auth = (email, token)
            requests.post(
                f"{url.rstrip('/')}/rest/api/2/issueLink",
                json={
                    "type": {"name": "Relates"},
                    "inwardIssue": {"key": key_origen},
                    "outwardIssue": {"key": key_destino},
                },
                auth=auth,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
        except Exception:
            pass  # Vinculación es best-effort


# --- Saneo de texto (AC-ACT-04, D11) ---


def sanear_texto_jira(texto: str, *, max_chars: int = MAX_CHARS_DESCRIPCION_JIRA) -> str:
    """Escapa HTML, markup de Jira y trunca (AC-ACT-04).

    1. Strip HTML tags
    2. Escape Jira wiki markup
    3. Truncar a max_chars con elipsis
    """
    # 1. Strip HTML tags
    clean = re.sub(r"<[^>]+>", "", texto)

    # 2. Escape Jira wiki markup
    # {code}...{code}, {color}, {panel}, etc.
    clean = re.sub(r"\{([^}]+)\}", r"{\1}", clean)  # ya escapado con backslash
    clean = re.sub(r"\{", "\\{", clean)
    clean = re.sub(r"\}", "\\}", clean)

    # 3. Truncar
    if len(clean) > max_chars:
        clean = clean[: max_chars - 3] + "..."

    return clean
