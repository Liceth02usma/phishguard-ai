# Feature Specification: API REST para el Frontend

**Feature Branch**: `feature/api-rest`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Una API REST que reemplace a la capa Express y al webhook de n8n, con el contrato del frontend."

## Context

**Problema**: PhishGuard solo tiene un poller de Gmail; el frontend no puede analizar correos ni consultar resultados.

**Objetivo**: una API REST que reemplace a la capa Express y al webhook de n8n, con el contrato del frontend.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M14 (14.3, 14.4 y 14.5) y `docs/ESPECIFICACION_INTERFAZ_PHISHING.md`.

**Depende de**: 11.

## User Scenarios & Testing

### User Story 1 - API REST con el contrato del frontend (Priority: P1)

Una API REST bajo `/api` con JSON UTF-8 y cabecera `X-API-Key` expone endpoints de salud, integraciones, muestras, análisis (POST en modos pegar/muestra/eml con `dry_run` por defecto), consulta/filtro/export CSV/feedback/borrado de análisis, métricas y jobs de Gmail. Errores con forma uniforme; las caídas de VT/modelo/RDAP devuelven 201 con `revision_manual`. Validación estricta, límite de tasa, CORS configurado, cabeceras de seguridad, CSV con protección contra inyección de fórmulas, OpenAPI generado, y el veredicto `revision_manual` en el contrato.

**Why this priority**: la API es la interfaz entre el backend y el frontend. Sin ella, el frontend no puede operar y el poller es la única entrada.

**Independent Test**: con `TestClient` y servicios simulados, verificar cada endpoint (forma, códigos, `dry_run` por defecto, 401 sin API key, 429 en el análisis 31, 201 con `revision_manual` ante caída de VT, escape CSV).

**Acceptance Scenarios**:

1. **AC-API-01**: cada endpoint cumple la forma de respuesta y los códigos de RF1 y RF2.
2. **AC-API-02**: `POST /analyses` con `modo=eml` y un adjunto devuelve `adjuntos[]` con SHA-256 y reputación.
3. **AC-API-03**: `dry_run` está activo por defecto y la respuesta lo refleja.
4. **AC-API-04**: la documentación OpenAPI refleja el contrato real (prueba de contrato).
5. **AC-API-05**: las métricas coinciden con las fórmulas del frontend sobre los datos de siembra.
6. **AC-API-06**: `GET /integraciones` no revela claves ni URLs internas.
7. **AC-API-07**: sin `X-API-Key` válida, todo endpoint salvo `health` devuelve 401.
8. **AC-API-08**: el CSV de un análisis cuyo asunto es `=HYPERLINK("http://x")` escapa la fórmula; con 5 001 resultados exporta 5 000.
9. **AC-API-09**: el análisis 31 en un minuto devuelve 429.
10. **AC-API-10**: una caída simulada de VirusTotal devuelve 201 con `revision_manual`.

### Edge Cases

- Sin `X-API-Key` (401 salvo health).
- Análisis 31 en un minuto (429).
- 5 001 resultados en export CSV (tope 5 000).
- Asunto `=HYPERLINK(...)` (inyección de fórmula).
- Caída de VirusTotal (201 con `revision_manual`).
- Multipart >25 MB (413).

## Requirements

### Functional Requirements

- **FR-001** (RF1): Endpoints bajo `/api` con JSON UTF-8 y cabecera `X-API-Key` (salvo `health`): `GET /health`; `GET /integraciones`; `GET /samples`; `POST /analyses` (JSON en modos `pegar` y `muestra`, o multipart en modo `eml`; `dry_run` activo por defecto); `GET /analyses/{id}`; `GET /analyses` (filtros `veredicto`, `severidad`, `q`, `desde`, `hasta`, `orden`, `pagina`, `limite` ≤ 50); `GET /analyses/export.csv`; `PATCH /analyses/{id}/feedback`; `DELETE /analyses/{id}`; `GET /metrics/summary` con `rango` 7d, 30d o 90d; `GET /jobs/gmail`; `POST /jobs/gmail/run` (misma `X-API-Key`; **sin roles** — constitución Art. V.8).
- **FR-002** (RF2): Errores con la forma `{ "error": { "codigo", "mensaje", "detalles" } }`: 401, 404, 413 (más de 25 MB), 422, 429, 500, 503. Las caídas de VirusTotal, el modelo o RDAP NO son errores: devuelven 201 con `revision_manual` y `verificaciones_incompletas`.
- **FR-003** (RF3): Validación estricta de toda entrada; límite de tasa (30 análisis por minuto por clave e IP); CORS solo para los orígenes configurados; cabeceras de seguridad.
- **FR-004** (RF4): La exportación CSV protege contra inyección de fórmulas (prefijo `'` en celdas que empiezan con `=`, `+`, `-` o `@`), con UTF-8 con BOM y un máximo de 5 000 filas.
- **FR-005** (RF5): `GET /integraciones` informa el estado de Mongo, VirusTotal (modo y cuota estimada), el modelo y Gmail sin revelar claves ni URLs internas.
- **FR-006** (RF6): Documentación OpenAPI generada.
- **FR-007** (RF7): Se agrega el veredicto `revision_manual` al contrato.

## Success Criteria

### Measurable Outcomes

- **SC-001**: el contrato OpenAPI refleja el comportamiento real de cada endpoint.
- **SC-002**: las caídas de servicios externos devuelven 201 con `revision_manual`, no errores 5xx.
- **SC-003**: el límite de tasa y la validación de entrada protegen la API.

## Assumptions

- **Fuera de alcance**: interfaz web. *Autenticación por roles: **decidido** — no habrá roles; una única `X-API-Key` para todos los endpoints autenticados (constitución Art. V.8).*
- **Hint para plan**: FastAPI con Pydantic, inyección de dependencias para servicios simulables, `TestClient`; archivos de rutas separados por recurso (ninguno > 500 líneas).
