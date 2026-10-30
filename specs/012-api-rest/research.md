# Research: API REST para el Frontend

**Spec**: 012 · **Date**: 2026-10-30

## D1 — Framework: FastAPI

**Decisión**: FastAPI con uvicorn como servidor ASGI.

**Rationale**: El hint del spec sugiere FastAPI. Genera OpenAPI automáticamente (FR-006, AC-API-04). Pydantic ya está en el proyecto. TestClient (httpx) para tests sin servidor real. Dependency injection nativa para services simulables.

**Alternativas**: Flask — sin OpenAPI automático, sin validación Pydantic nativa. Express — ya reemplazado por esta spec.

## D2 — Estructura del paquete

**Decisión**: `src/api/` con `app.py` (factory), `config.py` (settings), `deps.py` (DI), `middleware.py`, `errors.py`, `csv_export.py`, `routers/` (6 routers), `schemas/` (3 módulos).

**Rationale**: Rutas por recurso ≤ 200 líneas estimadas cada una. Schemas separados para reutilización entre routers y tests. Art. III.1: ningún archivo > 500 líneas.

**Alternativas**: Un solo archivo → superaría 500 líneas.

## D3 — Autenticación por X-API-Key

**Decisión**: Dependency `verificar_api_key()` que lee `X-API-Key` del header y la compara con `API_KEY` del entorno. Sin roles (Art. V.8). `GET /api/health` excluido (security=[]).

**Rationale**: AC-API-07: sin key válida → 401 salvo health. Una única clave compartida.

**Alternativas**: JWT → complejidad innecesaria sin roles. OAuth2 → overkill.

## D4 — Rate limiting

**Decisión**: Middleware in-memory con `dict[tuple[api_key, ip], list[timestamp]]`. Límite 30 análisis por minuto por clave e IP (FR-003). Solo aplica a `POST /api/analyses`. AC-API-09: análisis 31 → 429.

**Rationale**: Sin dependencias nuevas (no slowapi). In-memory es suficiente para un solo worker.

**Alternativas**: slowapi → dependencia nueva. Redis → infraestructura adicional.

## D5 — dry_run por defecto

**Decisión**: En el schema `AnalisisPegar`, `dry_run: bool = True` (Pydantic default). AC-API-03: la respuesta refleja `accion.simulada = True`.

**Rationale**: Art. V.2: dry_run por defecto. Consistente con spec 010.

## D6 — Degradación graceful (VT/modelo/RDAP caídos)

**Decisión**: Si `analyze_email()` lanza excepción por VT/modelo/RDAP, el endpoint `POST /analyses` captura y retorna 201 con `veredicto = "revision_manual"` y `verificaciones_incompletas` poblado. AC-API-10.

**Rationale**: FR-002: caídas de VT/modelo/RDAP NO son errores HTTP. 201 con revision_manual.

## D7 — CSV con protección contra inyección de fórmulas

**Decisión**: `csv_export.py` con función pura `generar_csv(analisis) -> str`. UTF-8 con BOM. Prefijo `'` en celdas que empiezan con `=`, `+`, `-` o `@`. Máximo 5000 filas (FR-004, AC-API-08).

**Rationale**: FR-004 explícito. Protección contra CSV injection (CWE-1236).

## D8 — OpenAPI generado automáticamente

**Decisión**: FastAPI genera `/openapi.json` y `/docs` automáticamente. AC-API-04: test de contrato que compara el schema generado con `openapi.yaml` del contrato.

**Rationale**: FR-006. FastAPI lo hace nativamente. El test de contrato verifica que coinciden.

## D9 — CORS y cabeceras de seguridad

**Decisión**: `CORSMiddleware` con orígenes de `CORS_ORIGINS` (env var). Cabeceras de seguridad vía middleware custom: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`.

**Rationale**: FR-003: CORS solo para orígenes configurados + cabeceras de seguridad.

## D10 — Muestras desde fixtures

**Decisión**: `GET /api/samples` lee los fixtures de `tests/fixtures/*.json` y los transforma al formato `Muestra`. Sin dependencia de MongoDB.

**Rationale**: Los fixtures ya existen en el repo. Forma [PROPUESTA] del contrato.

## D11 — Integraciones sin revelar claves

**Decisión**: `GET /api/integraciones` retorna estado de Mongo (ping), VT (modo + cuota estimada), modelo (disponibilidad), Gmail (OAuth status). NUNCA incluye claves, URIs internas ni tokens. AC-API-06.

**Rationale**: FR-005 explícito. Solo estado + modo + cuota estimada.

## D12 — Scope fence

**Decisión**: NO se modifica: `src/level2_agent/` (import), `src/level2_agent/persistencia/` (import), `src/gmail_integration/` (import). Se crea: `src/api/` (nuevo paquete). Se modifica: `pyproject.toml` (deps), `scripts/verify.py` (cov).

**Rationale**: Art. VI.1: solo lo que pide la spec.
