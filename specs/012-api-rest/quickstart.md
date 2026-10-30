# Quickstart: API REST para el Frontend

**Spec**: 012 · **Date**: 2026-10-30

## Prerequisites

- Python 3.11+, fastapi, uvicorn, httpx instalados
- Spec 011 (persistencia) merged en `main`
- `API_KEY` configurada en `.env`

## Validation Scenarios

### V1 — Health check (sin autenticación)

```powershell
# Con uvicorn
python -m uvicorn src.api.app:create_app --factory --port 8000
# En otra terminal:
curl http://localhost:8000/api/health
# Expected: {"estado": "ok"}
```

### V2 — Análisis con dry_run (AC-API-03)

```powershell
curl -X POST http://localhost:8000/api/analyses \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"modo": "pegar", "from": "test@test.com", "subject": "Test", "text": "Hello"}'
# Expected: 201, accion.simulada = true (dry_run default)
```

### V3 — 401 sin API key (AC-API-07)

```powershell
curl http://localhost:8000/api/analyses
# Expected: 401, error.codigo = "NO_AUTENTICADO"
```

### V4 — Métricas sobre siembra (AC-API-05)

```powershell
curl "http://localhost:8000/api/metrics/summary?rango=7d" -H "X-API-Key: test-key"
# Expected: total=100, por_veredicto={sin_indicadores:55, sospechoso:15, malicioso:30}
```

### V5 — CSV con escape de fórmula (AC-API-08)

```powershell
curl "http://localhost:8000/api/analyses/export.csv" -H "X-API-Key: test-key"
# Expected: text/csv con BOM, celdas con =HYPERLINK escapadas con prefijo '
```

### V6 — Rate limit (AC-API-09)

```powershell
# 31 análisis en un minuto → el 31ro devuelve 429
```

### V7 — Degradación VT (AC-API-10)

```powershell
# VT caído → 201 con veredicto="revision_manual" y verificaciones_incompletas
```

### V8 — OpenAPI contrato (AC-API-04)

```powershell
curl http://localhost:8000/openapi.json
# Expected: schema coincide con specs/012-api-rest/contracts/openapi.yaml
```

### V9 — Integraciones sin claves (AC-API-06)

```powershell
curl http://localhost:8000/api/integraciones -H "X-API-Key: test-key"
# Expected: estado de servicios, sin claves ni URLs internas
```

### V10 — Run all tests

```powershell
python -m pytest tests/unit/ -k "api" -v
```

**Expected**: all AC-API-* tests pass.
