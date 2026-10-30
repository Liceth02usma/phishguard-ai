# Data Model: API REST para el Frontend

**Spec**: 012 · **Date**: 2026-10-30

## Entities

### E1: AnalisisResponse (respuesta estándar)

Documento que devuelven `POST /analyses`, `GET /analyses/{id}`, y `items[]` en la lista.

| Campo | Tipo | Origen |
|---|---|---|
| `id` | `str` | MongoDB `_id` (str) |
| `origen` | `Origen` | `gmail` / `api` / `seed` |
| `modo` | `ModoAPI` | `pegar` / `eml` / `muestra` / `gmail` |
| `creado_en` | `datetime` | Timestamp del análisis |
| `duracion_ms` | `int` | Duración del análisis |
| `correo` | `CorreoResponse` | Remitente, asunto, cuerpo_enmascarado |
| `resultado` | `ResultadoResponse` | Score, veredicto, banderas, URLs, adjuntos, etc. |
| `accion` | `AccionResponse` | ejecutada, simulada |
| `retroalimentacion` | `Feedback | None` | confirmado / falso_positivo / None |

### E2: MetricasResponse

Respuesta de `GET /metrics/summary`.

| Campo | Tipo | Origen |
|---|---|---|
| `rango` | `Rango` | `7d` / `30d` / `90d` |
| `total` | `int` | Total análisis |
| `por_veredicto` | `dict[str, int]` | Conteo por veredicto |
| `por_ruta` | `dict[str, int]` | Conteo por ruta |
| `pct_sin_modelo` | `float` | % resuelto sin IA |
| `duracion_media_ms` | `float` | Duración media |
| `por_dia` | `list[PorDiaResponse]` | Desglose por día |
| `indicadores_frecuentes` | `list[IndicadorFrecuente]` | Top 10 |
| `tasa_falsos_positivos` | `float | None` | None sin retroalimentación |
| `consultas_vt` | `int` | Total consultas VT |
| `aciertos_cache_pct` | `float` | % aciertos caché |
| `revision_manual_total` | `int` | Total revision_manual |

### E3: ErrorEnvelope

Forma uniforme de errores (FR-002).

| Campo | Tipo | Valores |
|---|---|---|
| `error.codigo` | `str` | NO_AUTENTICADO, NO_ENCONTRADO, ENTRADA_GRANDE, VALIDACION, DEMASIADAS_SOLICITUDES, ERROR_INTERNO, SERVICIO_NO_DISPONIBLE |
| `error.mensaje` | `str` | Mensaje humano |
| `error.detalles` | `str | list | dict | None` | Detalle adicional |

### E4: AnalisisPaginado

Envoltorio de paginación.

| Campo | Tipo | Descripción |
|---|---|---|
| `items` | `list[AnalisisResponse]` | Página de resultados |
| `pagina` | `int` | Página actual (base 1) |
| `limite` | `int` | Tamaño de página (≤ 50) |
| `total` | `int` | Total de resultados |

## Constants

| Constante | Valor | Propósito |
|---|---|---|
| `RATE_LIMIT_POR_MINUTO` | `30` | FR-003: 30 análisis/min |
| `CSV_MAX_FILAS` | `5000` | FR-004: máximo filas CSV |
| `MULTIPART_MAX_MB` | `25` | FR-001: máximo tamaño EML |
| `LIMITE_PAGINACION_MAX` | `50` | FR-001: máximo por página |
| `LIMITE_PAGINACION_DEFAULT` | `50` | Default por página |
| `API_PREFIX` | `"/api"` | Prefijo de rutas |
| `CSV_BOM` | `"\ufeff"` | BOM UTF-8 para CSV |
| `CSV_PREFIJOS_PELIGROSOS` | `("=", "+", "-", "@")` | Prefijos de inyección de fórmulas |

## Invariants

1. **I1**: `GET /integraciones` nunca revela claves, URIs internas ni tokens.
2. **I2**: Sin `X-API-Key` válida → 401 (salvo `GET /health`).
3. **I3**: `dry_run=True` por defecto → `accion.simulada=True`.
4. **I4**: Caída VT/modelo/RDAP → 201 con `revision_manual`, nunca 5xx.
5. **I5**: CSV: celdas con prefijo peligroso llevan `'` prepended.
6. **I6**: CSV: máximo 5000 filas (5001 resultados → 5000 filas).
7. **I7**: Rate limit: análisis 31 en un minuto → 429.
