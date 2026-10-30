"""Adapter de Gmail para acciones (spec 010, M08, D2).

GmailAdapter Protocol define la interfaz.
GmailReal envuelve las funciones de gmail_reader.py.
"""

from __future__ import annotations

from typing import Protocol


class GmailAdapter(Protocol):
    """Protocol para el adapter de Gmail (D2)."""

    def etiquetar(self, msg_id: str, etiqueta: str) -> str:
        """Etiqueta el correo. Retorna el ID de la etiqueta."""
        ...

    def archivar(self, msg_id: str) -> None:
        """Quita de la bandeja (remove INBOX label)."""
        ...

    def marcar_leido(self, msg_id: str) -> None:
        """Quita UNREAD label."""
        ...

    def crear_etiqueta(self, nombre: str) -> str:
        """Crea la etiqueta si no existe. Retorna su ID."""
        ...


class GmailReal:
    """Adapter real que envuelve gmail_reader.py.

    Requiere un servicio Gmail autenticado.
    """

    def __init__(self, service: object) -> None:
        self._service = service

    def etiquetar(self, msg_id: str, etiqueta: str) -> str:
        """Etiqueta el correo y lo marca como leído."""
        from src.gmail_integration.gmail_reader import move_to_label

        label_id = move_to_label(self._service, msg_id, etiqueta)  # type: ignore[no-untyped-call]
        return str(label_id) if label_id else ""

    def archivar(self, msg_id: str) -> None:
        """Quita de la bandeja (remove INBOX label)."""
        self._service.messages().modify(  # type: ignore[union-attr]
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["INBOX"]},
        ).execute()

    def marcar_leido(self, msg_id: str) -> None:
        """Quita UNREAD label."""
        from src.gmail_integration.gmail_reader import mark_as_read

        mark_as_read(self._service, msg_id)  # type: ignore[no-untyped-call]

    def crear_etiqueta(self, nombre: str) -> str:
        """Crea la etiqueta si no existe. Retorna su ID."""
        result = (
            self._service.labels()  # type: ignore[union-attr]
            .list(userId="me")
            .execute()
        )
        for label in result.get("labels", []):
            if label.get("name") == nombre:
                return str(label["id"])
        new_label = (
            self._service.labels()  # type: ignore[union-attr]
            .create(userId="me", body={"name": nombre})
            .execute()
        )
        return str(new_label["id"])
