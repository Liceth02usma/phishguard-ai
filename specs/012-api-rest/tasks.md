# Tasks: API REST para el Frontend

**Spec**: 012 · **Branch**: `feature/api-rest` · **Date**: 2026-10-30

## Phase 1: Setup

- [ ] T001: Crear paquete `src/api/` con subpaquetes `routers/` y `schemas/` + módulos vacíos
- [ ] T002: Añadir dependencias `fastapi`, `uvicorn`, `python-multipart`, `httpx` a `requirements.txt`
- [ ] T003: Añadir override mypy strict para `src.api` en `pyproject.toml`
- [ ] T004: Añadir `--cov=src/api` y path en `scripts/verify.py`

## Phase 2: Fundacional

- [ ] T005: Implementar `config.py` — Settings con API_KEY, CORS_ORIGINS, RATE_LIMIT, etc.
- [ ] T006: Implementar `errors.py` — ErrorEnvelope, códigos, exception handlers
- [ ] T007: Implementar `deps.py` — verificar_api_key(), get_repo(), get_current_time()
- [ ] T008: Implementar `middleware.py` — RateLimiter (30/min), security headers, CORS
- [ ] T009: Implementar `schemas/comunes.py` — Veredicto, Severidad, Ruta, Modo, Origen, Feedback, Rango, Pagination
- [ ] T010: Implementar `schemas/analisis.py` — Request/response models (AnalisisPegar, AnalisisMuestra, AnalisisEml, AnalisisResponse, etc.)
- [ ] T011: Implementar `schemas/metricas.py` — MetricasResponse, PorDiaResponse, IndicadorFrecuente
- [ ] T012: Implementar `csv_export.py` — generar_csv() con BOM, escape fórmulas, límite 5000 filas
- [ ] T013: Implementar `app.py` — create_app() factory con routers, middleware, exception handlers
- [ ] T014: Implementar `__init__.py` — public API exports

## Phase 3: Routers

- [ ] T015: Implementar `routers/salud.py` — GET /api/health
- [ ] T016: Implementar `routers/integraciones.py` — GET /api/integraciones (sin claves)
- [ ] T017: Implementar `routers/muestras.py` — GET /api/samples
- [ ] T018: Implementar `routers/analisis.py` — POST /api/analyses (3 modos + dry_run)
- [ ] T019: Implementar `routers/analisis.py` — GET /api/analyses (filtros + paginación)
- [ ] T020: Implementar `routers/analisis.py` — GET /api/analyses/{id}
- [ ] T021: Implementar `routers/analisis.py` — GET /api/analyses/export.csv
- [ ] T022: Implementar `routers/analisis.py` — PATCH /api/analyses/{id}/feedback
- [ ] T023: Implementar `routers/analisis.py` — DELETE /api/analyses/{id}
- [ ] T024: Implementar `routers/metricas.py` — GET /api/metrics/summary
- [ ] T025: Implementar `routers/jobs.py` — GET/POST /api/jobs/gmail

## Phase 4: Pruebas TDD (AC-API-01..10)

- [ ] T026: Test AC-API-01 — cada endpoint cumple forma de respuesta y códigos
- [ ] T027: Test AC-API-02 — POST /analyses modo=eml con adjunto devuelve sha256 y reputación
- [ ] T028: Test AC-API-03 — dry_run activo por defecto, respuesta lo refleja
- [ ] T029: Test AC-API-04 — OpenAPI generado coincide con contrato
- [ ] T030: Test AC-API-05 — métricas coinciden con fórmulas sobre datos de siembra
- [ ] T031: Test AC-API-06 — GET /integraciones no revela claves ni URLs internas
- [ ] T032: Test AC-API-07 — sin X-API-Key → 401 salvo health
- [ ] T033: Test AC-API-08 — CSV escapa fórmulas; 5001 resultados → 5000 filas
- [ ] T034: Test AC-API-09 — análisis 31 en un minuto → 429
- [ ] T035: Test AC-API-10 — caída VT → 201 con revision_manual

## Phase 5: Pulido

- [ ] T036: ruff + mypy strict sobre `src/api/`
- [ ] T037: Verificar longitud archivos ≤500 líneas
- [ ] T038: Actualizar README.md con sección API REST
- [ ] T039: Actualizar AGENTS.md con arquitectura de API
- [ ] T040: Marcar tareas completadas en tasks.md
