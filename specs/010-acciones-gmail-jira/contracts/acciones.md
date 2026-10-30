# Contract: Ejecutor de Acciones

**Spec**: 010 · **Module**: M08 · **Package**: `src.level2_agent.acciones`

## §1 — Orquestador

```python
def ejecutar_acciones(
    entrada: EntradaAcciones,
    *,
    gmail: GmailAdapter | None = None,
    jira: JiraAdapter | None = None,
    ahora: datetime | None = None,
) -> ResultadoAcciones:
    """Ejecuta acciones según veredicto.

    1. Consulta idempotencia (message_id ya procesado → retorna sin ejecutar).
    2. Si DRY_RUN activo → registra simulacro sin ejecutar.
    3. Resuelve acciones desde la tabla (D3).
    4. Ejecuta cada acción via adapter.
    5. Si Jira falla → registra error, continúa con Gmail (D10).
    6. Registra resultado en MongoDB para idempotencia.
    7. Retorna ResultadoAcciones.
    """
```

**Precondiciones**: `entrada.veredicto` es uno de los 4 valores válidos. `entrada.message_id` no vacío.

**Postcondiciones**: `ResultadoAcciones.acciones` tiene ≥ 1 elemento. Ninguna acción elimina correos (I1).

## §2 — Adapter Gmail

```python
class GmailAdapter(Protocol):
    def etiquetar(self, msg_id: str, etiqueta: str) -> str:
        """Etiqueta el correo. Retorna el ID de la etiqueta."""

    def archivar(self, msg_id: str) -> None:
        """Quita de la bandeja (remove INBOX label)."""

    def marcar_leido(self, msg_id: str) -> None:
        """Quita UNREAD label."""

    def crear_etiqueta(self, nombre: str) -> str:
        """Crea la etiqueta si no existe. Retorna su ID."""
```

## §3 — Adapter Jira

```python
class JiraAdapter(Protocol):
    def crear_ticket(self, campos: dict[str, Any]) -> ResultadoJira:
        """Crea un ticket. Retorna issue_key o error."""

    def buscar_por_huella(self, huella: str) -> str | None:
        """Busca ticket existente por huella de campaña. Retorna issue_key o None."""

    def vincular(self, key_origen: str, key_destino: str) -> None:
        """Vincula dos tickets (issue links)."""
```

```python
class ResultadoJira(BaseModel):
    exito: bool
    issue_key: str | None = None
    url: str | None = None
    error: str | None = None
```

## §4 — Tabla de mapeo

```python
def resolver_acciones(veredicto: Veredicto) -> list[Accion]:
    """Retorna las acciones para el veredicto dado (FR-001)."""
```

| Veredicto | Acciones |
|---|---|
| `malicioso` | `[ETIQUETAR_PHISHING, ARCHIVAR, CREAR_TICKET]` |
| `sospechoso` | `[ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]` |
| `revision_manual` | `[ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]` |
| `sin_indicadores` | `[MARCAR_LEIDO]` |

## §5 — Huella de campaña

```python
def calcular_huella(remitente: str, asunto: str, urls: list[str]) -> str:
    """Calcula huella SHA-256 truncada para deduplicación de tickets (FR-004).

    huella = SHA-256(remitente + asunto_normalizado + dominios_ordenados)[:16]
    """
```

## §6 — Saneo de texto Jira

```python
def sanear_texto_jira(texto: str, *, max_chars: int = 3000) -> str:
    """Escapa HTML, markup de Jira y trunca (AC-ACT-04)."""
```
