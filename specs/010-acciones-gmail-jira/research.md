# Research: Acciones Idempotentes en Gmail y Jira

**Spec**: 010 · **Date**: 2026-10-29

## D1 — Estructura del paquete

**Decisión**: `src/level2_agent/acciones/` con 6 módulos (`modelos.py`, `tabla.py`, `gmail_adapter.py`, `jira_adapter.py`, `huella.py`, `ejecutor.py`) + `__init__.py`.

**Rationale**: Sigue el patrón de specs 003–009 (un paquete por spec). Cada módulo tiene una responsabilidad (Art. III.7). El orquestador (`ejecutor.py`) consume la tabla y los adapters.

**Alternativas**: Un solo archivo `acciones.py` → rechazado por Art. III.1 (superaría 500 líneas con adapters + tabla + huella + ejecutor).

## D2 — Adapter pattern para Gmail y Jira

**Decisión**: Protocol `GmailAdapter` con métodos `etiquetar(msg_id, etiqueta)`, `archivar(msg_id)`, `marcar_leido(msg_id)`, `crear_etiqueta(nombre) -> str`. Protocol `JiraAdapter` con `crear_ticket(campos) -> ResultadoJira`, `buscar_ticket(huella) -> str | None`, `vincular_ticket(key, key_relacionado) -> None`.

**Rationale**: Permite dobles de prueba sin servicios reales (AC-ACT-01..08). El poller inyecta `GmailReal` (que envuelve `gmail_reader.py`), los tests inyectan `GmailDoble`. Mismo patrón que `ModeloLLM` en spec 009.

**Alternativas**: Monkeypatching directo → frágil, no tipado. Herencia → más rígido que Protocol.

## D3 — Tabla de mapeo veredicto→acciones (FR-001)

**Decisión**: Tabla como datos en `tabla.py` (diccionario `Veredicto → list[Accion]`). Acciones posibles: `ETIQUETAR_PHISHING`, `ETIQUETAR_REVISAR`, `ARCHIVAR`, `MARCAR_LEIDO`, `CREAR_TICKET`, `CREAR_TICKET_BAJA`.

Mapeo literal de FR-001:
| Veredicto | Acciones |
|---|---|
| `malicioso` | ETIQUETAR_PHISHING, ARCHIVAR, CREAR_TICKET |
| `sospechoso` | ETIQUETAR_REVISAR, CREAR_TICKET_BAJA |
| `revision_manual` | ETIQUETAR_REVISAR, CREAR_TICKET_BAJA |
| `sin_indicadores` | MARCAR_LEIDO |

**Rationale**: Tabla de decisión obligatoria (Art. II.2). Datos, no lógica condicional — fácil de probar y auditar.

**Alternativas**: `if/elif` en el ejecutor → menos auditable, más propenso a errores.

## D4 — DRY_RUN por defecto (FR-002, Art. V.2)

**Decisión**: Variable de entorno `ACCIONES_DRY_RUN` (default `"true"`). Cuando está activo, el ejecutor registra la acción que habría ejecutado pero NO llama a ningún adapter de escritura. `ResultadoAccion.ejecutada = False`, `ResultadoAccion.motivo = "dry_run"`.

**Rationale**: Art. V.2 exige DRY_RUN como valor por defecto. En producción se pone `ACCIONES_DRY_RUN=false` explícitamente.

**Alternativas**: Flag en la llamada → se puede olvidar. Env var es más seguro y auditable.

## D5 — Idempotencia por message_id (FR-003)

**Decisión**: Colección MongoDB `phishguard.acciones_ejecutadas` con documento `{message_id, veredicto, acciones: [...], fecha}` y índice único en `message_id`. Antes de ejecutar, se consulta si ya existe. Si existe, se retorna el resultado anterior sin re-ejecutar. Fallback in-memory (dict) si Mongo no está disponible.

**Rationale**: El `message_id` de Gmail es único e inmutable. Procesar el mismo mensaje dos veces (poller lo lee, se cae, lo lee de nuevo) no repite acciones.

**Alternativas**: Set en memoria → se pierde al reiniciar. Sin idempotencia → riesgo de tickets duplicados y etiquetas repetidas.

## D6 — Huella de campaña para deduplicación de tickets (FR-004)

**Decisión**: `huella = SHA-256(remitente + asunto_normalizado + dominios_urls_ordenados)[:16]`. `asunto_normalizado` = lower + strip + collapse whitespace + remove RE:/FWD: prefixes. `dominios_urls_ordenados` = sorted(set(dominio_registrable para cada URL)). Se busca en Jira por custom field `huella_campaña` antes de crear. Si existe, se vincula en vez de crear nuevo.

**Rationale**: Mismo remitente + mismo asunto (campaña de phishing) + mismos dominios = misma campaña. SHA-256 evita inyección en la búsqueda de Jira. Truncado a 16 chars hex para custom field corto.

**Alternativas**: Búsqueda por JQL de summary → frágil (cambios de formato). Huella sin URLs → demasiado amplia (campañas diferentes con mismo asunto).

## D7 — Nunca eliminar correos (FR-005)

**Decisión**: La tabla de acciones (D3) NO incluye ninguna acción de eliminación. `GmailAdapter` NO expone método `eliminar`. OAuth scopes permanecen como `gmail.readonly` + `gmail.modify` (sin `gmail.delete`). Se agrega test AST que verifica que ningún archivo en `acciones/` contiene `trash`, `delete` o `eliminar`.

**Rationale**: FR-005 explícito. Art. V.2 (acciones las decide código determinista). Los scopes OAuth mínimos ya concedidos no incluyen delete.

**Alternativas**: Ninguna — es un requisito duro.

## D8 — Auditoría de acciones (FR-006)

**Decisión**: Cada acción ejecutada o simulada se registra en `ResultadoAccion` con: `accion`, `destino` (Gmail/Jira), `identificador` (msg_id o issue_key), `ejecutada` (bool), `motivo` ("exito"/"dry_run"/"idempotencia"/"error_jira"), `timestamp`. El orquestador retorna `ResultadoAcciones` con la lista completa. El poller lo loguea.

**Rationale**: FR-006 exige registrar cada acción. Trazabilidad para debugging y compliance.

**Alternativas**: Log a archivo → no estructurado. Solo en MongoDB → no disponible en tests.

## D9 — Notificación sin "seguro" (FR-007, Art. V.1)

**Decisión**: Para `sin_indicadores`, la notificación usa "Sin indicadores de riesgo detectados" en vez de "seguro" o "confiable". El campo `PhishingReport.resumen` ya usa "Tráfico seguro confirmado" (preexistente) — no se modifica (Art. V.1 permite "seguro" en descripciones técnicas, solo lo prohíbe como veredicto final categórico).

**Rationale**: Art. V.1: la palabra "seguro" se prohíbe como **veredicto final categórico del producto**. El veredicto es `sin_indicadores`, no "seguro". Las descripciones técnicas del reporte pueden usar la palabra.

**Alternativas**: Cambiar "Tráfico seguro confirmado" → fuera de alcance (Art. VI.1).

## D10 — Resiliencia ante fallo de Jira (AC-ACT-08)

**Decisión**: Si `JiraAdapter.crear_ticket()` lanza excepción o retorna error, el ejecutor: (1) registra el error en `ResultadoAccion.motivo = "error_jira"`, (2) continúa con las acciones de Gmail (no se cancelan), (3) NO reintenta (evita bucle), (4) NO marca el correo como procesado para idempotencia en la parte de Jira (para que se reintente en la próxima ejecución del poller). Las acciones de Gmail sí se registran como procesadas.

**Rationale**: AC-ACT-08 explícito: si Jira falla, Gmail se mantiene, error se registra, no bucle.

**Alternativas**: Reintentar Jira → bucle potencial. Cancelar todo → pierde acciones de Gmail.

## D11 — Escapar y truncar texto del atacante (AC-ACT-04)

**Decisión**: `sanear_texto_jira(texto, max_chars=3000) -> str`: (1) strip HTML tags, (2) escape Jira wiki markup (`{*}`, `{code}`, etc.), (3) truncar a `max_chars` con elipsis. Aplicado a `summary` (max 190 chars, ya existente) y `description` (max 3000 chars). El asunto del correo se sanea antes de incluirlo en el ticket.

**Rationale**: AC-ACT-04: asunto con HTML, markup de Jira o 10 000 caracteres debe escaparse y truncarse.

**Alternativas**: Sin saneo → XSS en Jira. Solo truncar → markup roto.

## D12 — Scope fence

**Decisión**: NO se modifica: `src/level2_agent/decision/` (import solo), `src/level2_agent/agente/` (import solo), `src/level2_agent/models.py` (import solo), `src/gmail_integration/gmail_reader.py` (se envuelve, no se modifica), `src/level2_agent/tools/jira_integration.py` (se envuelve, no se modifica). Se modifica: `src/gmail_integration/gmail_poller.py` (wiring del ejecutor de acciones).

**Rationale**: Art. VI.1: solo lo que pide la spec. El poller es el punto de wiring natural.
