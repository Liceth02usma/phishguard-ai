# Data Model: Acciones Idempotentes en Gmail y Jira

**Spec**: 010 · **Date**: 2026-10-29

## Entities

### E1: EntradaAcciones

Entrada del ejecutor de acciones: veredicto + datos del correo + resultado del análisis.

| Campo | Tipo | Restricción | Origen |
|---|---|---|---|
| `veredicto` | `Literal["malicioso","sospechoso","revision_manual","sin_indicadores"]` | requerido | spec 008 `VeredictoMotor.veredicto` |
| `nivel_severidad` | `Literal["Critico","Alto","Medio","Bajo"]` | requerido | spec 008 `VeredictoMotor.nivel_severidad` |
| `message_id` | `str` | requerido, len ≥ 1 | `EmailData.message_id` |
| `remitente` | `str` | requerido | `EmailData.from` (primer campo) |
| `asunto` | `str` | requerido | `EmailData.subject` |
| `urls` | `list[str]` | default `[]` | `EmailData.urls` |
| `reporte` | `PhishingReport` | requerido | `analyze_email()` output |
| `origen` | `Literal["gmail","api"]` | requerido | `EmailData.origen` |

### E2: ResultadoAccion

Registro de una acción individual ejecutada o simulada.

| Campo | Tipo | Restricción | Origen |
|---|---|---|---|
| `accion` | `Accion` (enum) | requerido | Tabla de mapeo (D3) |
| `destino` | `Literal["gmail","jira"]` | requerido | Gmail o Jira |
| `identificador` | `str` | requerido | msg_id o issue_key |
| `ejecutada` | `bool` | requerido | True si se ejecutó, False si simulacro/idempotencia |
| `motivo` | `Literal["exito","dry_run","idempotencia","error_jira","error_gmail"]` | requerido | Razón del$0 |
| `timestamp` | `datetime` | requerido | Reloj inyectado |
| `detalle` | `str | None` | default `None` | Info adicional (issue_key, error msg) |

### E3: ResultadoAcciones

Salida del ejecutor: lista de acciones + resumen.

| Campo | Tipo | Restricción | Origen |
|---|---|---|---|
| `acciones` | `list[ResultadoAccion]` | requerido | Lista de acciones ejecutadas/simuladas |
| `huella_campaña` | `str | None` | default `None` | Huella calculada (D6) |
| `ticket_key` | `str | None` | default `None` | Issue key de Jira (si se creó/vinculó) |
| `procesado` | `bool` | requerido | True si se registró en MongoDB para idempotencia |

### E4: Accion (enum)

Acciones posibles según la tabla de mapeo (D3).

| Valor | Destino | Descripción |
|---|---|---|
| `ETIQUETAR_PHISHING` | Gmail | Etiquetar como "Phishing Alertas" |
| `ETIQUETAR_REVISAR` | Gmail | Etiquetar como "Revisar Seguridad" |
| `ARCHIVAR` | Gmail | Sacar de la bandeja (quitar INBOX) |
| `MARCAR_LEIDO` | Gmail | Quitar UNREAD |
| `CREAR_TICKET` | Jira | Crear ticket de prioridad Alta/Crítico |
| `CREAR_TICKET_BAJA` | Jira | Crear ticket de prioridad Media/Baja |

## Constants

| Constante | Valor | Propósito |
|---|---|---|
| `ETIQUETA_PHISHING` | `"Phishing Alertas"` | Nombre de label en Gmail (ya existente) |
| `ETIQUETA_REVISAR` | `"Revisar Seguridad"` | Nombre de label nuevo en Gmail |
| `DRY_RUN_DEFAULT` | `True` | DRY_RUN activo por defecto (Art. V.2) |
| `MAX_CHARS_DESCRIPCION_JIRA` | `3000` | Límite de descripción del ticket |
| `MAX_CHARS_SUMMARY_JIRA` | `190` | Límite de summary del ticket (ya existente) |
| `HUELLA_LONGITUD` | `16` | Longitud de la huella de campaña (hex) |
| `JIRA_PROYECTO` | `"SCRUM"` | Proyecto Jira (ya existente) |
| `JIRA_TIPO_TICKET` | `"Task"` | Tipo de issue (ya existente) |

## Invariants

1. **I1**: La tabla de mapeo (D3) NO contiene ninguna acción de eliminación.
2. **I2**: `ResultadoAccion.motivo == "exito"` implica `ResultadoAccion.ejecutada == True`.
3. **I3**: `ResultadoAccion.motivo == "dry_run"` implica `ResultadoAccion.ejecutada == False`.
4. **I4**: `ResultadoAccion.motivo == "idempotencia"` implica `ResultadoAccion.ejecutada == False`.
5. **I5**: Si `EntradaAcciones.origen == "api"`, no se ejecutan acciones de Gmail (solo Jira).
