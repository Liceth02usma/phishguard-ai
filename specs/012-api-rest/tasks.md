# Tasks: API REST para el Frontend

**Spec**: 012 · **Branch**: `feature/api-rest` · **Date**: 2026-10-30

## Phase 1: Setup

- [X] T001: Crear paquete `src/api/` con subpaquetes `routers/` y `schemas/` + módulos vacíos
- [X] T002: Añadir dependencias `fastapi`, `uvicorn`, `python-multipart`, `httpx` a `requirements.txt`
- [X] T003: Añadir override mypy strict para `src.api` en `pyproject.toml`
- [X] T004: Añadir `--cov=src/api` y path en `scripts/verify.py`

## Phase 2: Fundacional

- [X] T005: Implementar `config.py` — Settings con API_KEY, CORS_ORIGINS, RATE_LIMIT, etc.
- [X] T006: Implementar `errors.py` — ErrorEnvelope, códigos, exception handlers
- [X] T007: Implementar `deps.py` — verificar_api_key(), get_repo(), get_current_time()
- [X] T008: Implementar `middleware.py` — RateLimiter (30/min), security headers, CORS
- [X] T009: Implementar `schemas/comunes.py` — Veredicto, Severidad, Ruta, Modo, Origen, Feedback, Rango, Pagination
- [X] T010: Implementar `schemas/analisis.py` — Request/response models (AnalisisPegar, AnalisisMuestra, AnalisisEml, AnalisisResponse, etc.)
- [X] T011: Implementar `schemas/metricas.py` — MetricasResponse, PorDiaResponse, IndicadorFrecuente
- [X] T012: Implementar `csv_export.py` — generar_csv() con BOM, escape fórmulas, límite 5000 filas
- [X] T013: Implementar `app.py` — create_app() factory con routers, middleware, exception handlers
- [X] T014: Implementar `__init__.py` — public API exports

## Phase 3: Routers

- [X] T015: Implementar `routers/salud.py` — GET /api/health
- [X] T016: Implementar `routers/integraciones.py` — GET /api/integraciones (sin claves)
- [X] T017: Implementar `routers/muestras.py` — GET /api/samples
- [X] T018: Implementar `routers/analisis.py` — POST /api/analyses (3 modos + dry_run)
- [X] T019: Implementar `routers/analisis.py` — GET /api/analyses (filtros + paginación)
- [X] T020: Implementar `routers/analisis.py` — GET /api/analyses/{id}
- [X] T021: Implementar `routers/analisis.py` — GET /api/analyses/export.csv
- [X] T022: Implementar `routers/analisis.py` — PATCH /api/analyses/{id}/feedback
- [X] T023: Implementar `routers/analisis.py` — DELETE /api/analyses/{id}
- [X] T024: Implementar `routers/metricas.py` — GET /api/metrics/summary
- [X] T025: Implementar `routers/jobs.py` — GET/POST /api/jobs/gmail

## Phase 4: Pruebas TDD (AC-API-01..10)

- [X] T026: Test AC-API-01 — cada endpoint cumple forma de respuesta y códigos
- [X] T027: Test AC-API-02 — POST /analyses modo=eml con adjunto devuelve sha256 y reputación
- [X] T028: Test AC-API-03 — dry_run activo por defecto, respuesta lo refleja
- [X] T029: Test AC-API-04 — OpenAPI generado coincide con contrato
- [X] T030: Test AC-API-05 — métricas coinciden con fórmulas sobre datos de siembra
- [X] T031: Test AC-API-06 — GET /integraciones no revela claves ni URLs internas
- [X] T032: Test AC-API-07 — sin X-API-Key → 401 salvo health
- [X] T033: Test AC-API-08 — CSV escapa fórmulas; 5001 resultados → 5000 filas
- [X] T034: Test AC-API-09 — análisis 31 en un minuto → 429
- [X] T035: Test AC-API-10 — caída VT → 201 con revision_manual

## Phase 5: Pulido

- [X] T036: ruff + mypy strict sobre `src/api/`
- [X] T037: Verificar longitud archivos ≤500 líneas
- [X] T038: Actualizar README.md con sección API REST
- [X] T039: Actualizar AGENTS.md con arquitectura de API
- [X] T040: Marcar tareas completadas en tasks.md
