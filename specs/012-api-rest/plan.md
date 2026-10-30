# Implementation Plan: API REST para el Frontend

**Branch**: `feature/api-rest` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

## Summary

API REST bajo `/api` con FastAPI que expone 12 endpoints: salud, integraciones,
muestras, análisis (POST/GET/GET{id}/PATCH feedback/DELETE/export CSV), métricas
y jobs de Gmail. Autenticación por `X-API-Key` (sin roles, Art. V.8). `dry_run`
activo por defecto. Límite de tasa 30/min. CSV con protección contra inyección
de fórmulas. OpenAPI generado automáticamente. Caídas de VT/modelo/RDAP → 201
con `revision_manual`.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: fastapi, uvicorn, python-multipart (nuevas); pydantic, pymongo (ya instaladas)

**Testing**: pytest + httpx TestClient (FastAPI). Cero servicios reales (MongoDB, VT, Gmail simulados).

**Target Platform**: Windows (primary), cross-platform

**Project Type**: web service (FastAPI application)

**Performance Goals**: Respuesta < 500ms para endpoints de lectura. Análisis asíncrono si es necesario.

**Constraints**: Sin roles (Art. V.8). `dry_run` por defecto (Art. V.2). PII enmascarada (Art. V.4). Archivos ≤ 500 líneas (Art. III.1). CSV ≤ 5000 filas (FR-004). Rate limit 30/min (FR-003).

**Scale/Scope**: ~30 análisis/minuto por API key. Frontend como único consumidor.

## Constitution Check

| Artículo | Requisito | Estado | Nota |
|---|---|---|---|
| Art. 0 | Integridad de instrucciones | PASS | API es código determinista, no modelo |
| Art. I.1 | Rama creada primero | PASS | `feature/api-rest` ya existe |
| Art. I.5 | Conventional Commits | PASS | `feat(api): …` |
| Art. II.1 | Pruebas primero | PASS | TDD con TestClient |
| Art. II.2 | ≥3 técnicas | PASS | Partición (veredictos), valores límite (rate limit, CSV), contrato (OpenAPI) |
| Art. II.3 | Cobertura ≥80% | PLAN | Objetivo del plan |
| Art. III.1 | Archivos ≤500 líneas | PASS | Rutas separadas por recurso (5 routers) |
| Art. III.4 | mypy --strict | PASS | Override en pyproject.toml |
| Art. III.5 | Patrones de diseño | PASS | Dependency Injection (FastAPI), Repository (spec 011), Adapter |
| Art. III.6 | Sin números mágicos | PASS | Constantes en config |
| Art. V.1 | "seguro" jamás como veredicto | PASS | Veredicto del motor de decisión (spec 008) |
| Art. V.2 | dry_run por defecto | PASS | FR-001, AC-API-03 |
| Art. V.4 | Datos personales enmascarados | PASS | PII enmascarada antes de responder |
| Art. V.8 | Sin roles, una única API key | PASS | FR-001, AC-API-07 |
| Art. VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..007; fuera: UI web |

## Project Structure

### Documentation (this feature)

```text
specs/012-api-rest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api-rest.md          (ya existe)
│   ├── openapi.yaml          (ya existe)
│   └── integracion-frontend.md (ya existe)
└── tasks.md
```

### Source Code (repository root)

```text
src/api/
├── __init__.py
├── app.py                # FastAPI application factory
├── config.py             # Settings (API key, CORS, rate limit)
├── deps.py               # Dependency injection (auth, repo, services)
├── middleware.py          # Rate limiter, security headers, CORS
├── errors.py             # Error envelope models + exception handlers
├── routers/
│   ├── __init__.py
│   ├── salud.py          # GET /api/health
│   ├── integraciones.py  # GET /api/integraciones
│   ├── muestras.py       # GET /api/samples
│   ├── analisis.py       # POST/GET/GET{id}/PATCH/DELETE /api/analyses
│   ├── metricas.py       # GET /api/metrics/summary
│   └── jobs.py           # GET/POST /api/jobs/gmail
├── schemas/
│   ├── __init__.py
│   ├── analisis.py       # Request/response models for analyses
│   ├── metricas.py       # Response models for metrics
│   └── comunes.py        # Shared enums, error models, pagination
└── csv_export.py         # CSV generation with formula injection protection

tests/unit/
├── dobles_api.py         # Test doubles (fake repos, fake services)
├── test_ac_api_01_forma_respuesta.py
├── test_ac_api_02_adjuntos_eml.py
├── test_ac_api_03_dry_run_default.py
├── test_ac_api_04_openapi_contrato.py
├── test_ac_api_05_metricas_siembra.py
├── test_ac_api_06_integraciones_sin_claves.py
├── test_ac_api_07_auth_401.py
├── test_ac_api_08_csv_escape.py
├── test_ac_api_09_rate_limit.py
└── test_ac_api_10_degradacion_vt.py
```

**Structure Decision**: Rutas separadas por recurso (6 routers) para cumplir Art. III.1 (≤500 líneas). Schemas separados de routers para reutilización.

## Complexity Tracking

Sin violaciones a la constitución.
