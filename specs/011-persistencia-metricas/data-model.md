# Data Model: Persistencia y Métricas de Análisis

**Spec**: 011 · **Date**: 2026-10-30

## Entities

### E1: AnalisisPersistido

Documento que se guarda en MongoDB `phishguard.analyses`.

| Campo | Tipo | Restricción | Origen |
|---|---|---|---|
| `message_id` | `str` | requerido, índice | `EmailData.message_id` |
| `origen` | `Literal["gmail","api","siembra"]` | requerido | Gmail poller / API / siembra |
| `modo` | `Literal["produccion","dry_run"]` | requerido | `ACCIONES_DRY_RUN` |
| `fecha` | `datetime` | requerido, índice | Timestamp del análisis |
| `duracion_ms` | `int` | requerido, ≥ 0 | Duración del análisis |
| `correo_enmascarado` | `dict` | requerido | `enmascarar_para_terceros(email_data)` |
| `score_final` | `int` | 0–100 | Score compuesto |
| `ruta` | `Literal["reglas","heuristica","ia"]` | requerido | `VeredictoMotor.ruta` |
| `veredicto` | `Veredicto` (4 valores) | requerido, índice | `VeredictoMotor.veredicto` |
| `nivel_severidad` | `NivelSeveridad` (4 valores) | requerido | `VeredictoMotor.nivel_severidad` |
| `banderas` | `list[str]` | default `[]` | Banderas activadas |
| `reglas_aplicadas` | `list[str]` | default `[]` | Reglas R1–R5 que aplicaron |
| `autenticacion` | `dict` | default `{}` | SPF/DKIM/DMARC |
| `urls` | `list[str]` | default `[]` | URLs del correo |
| `adjuntos_nombres` | `list[str]` | default `[]` | Nombres de adjuntos (sin contenido) |
| `version_pesos` | `str` | requerido | Versión del modelo de scoring |
| `version_modelo` | `str` | requerido | Versión del modelo LLM |
| `accion` | `str | None` | default `None` | Acción ejecutada |
| `retroalimentacion` | `Literal["confirmado","falso_positivo",None]` | default `None` | Feedback del usuario |
| `expira_en` | `datetime` | requerido | TTL: fecha + 90 días |

### E2: Metricas

Resultado de las agregaciones.

| Campo | Tipo | Descripción |
|---|---|---|
| `total` | `int` | Total de análisis |
| `por_veredicto` | `dict[Veredicto, int]` | Conteo por veredicto |
| `pct_sin_modelo` | `float` | % resuelto sin IA (ruta heurística o reglas) |
| `duracion_media_ms` | `float` | Duración media en ms |
| `por_dia` | `list[dict]` | `[{fecha, total, malicioso, sospechoso, revision_manual, sin_indicadores}]` |
| `indicadores_frecuentes` | `list[tuple[str, int]]` | Top 10 indicadores más frecuentes |
| `tasa_falsos_positivos` | `float | None` | None si no hay retroalimentación |
| `consultas_vt` | `int` | Total consultas VT |
| `aciertos_cache` | `int` | Total aciertos de caché VT |

## Constants

| Constante | Valor | Propósito |
|---|---|---|
| `RETENCION_ANALISIS_DIAS` | `90` | TTL de `analyses` |
| `RETENCION_FALLIDOS_DIAS` | `30` | TTL de `analyses_fallidos` |
| `RETENCION_VT_CACHE_DIAS` | `7` | TTL de `vt_cache` (ya existente) |
| `RETENCION_VT_CUOTA_DIAS` | `2` | TTL de `vt_cuota` |
| `ZONA_HORARIA` | `"America/Bogota"` | Zona para `por_dia` |
| `SIEMBRA_TOTAL` | `100` | Total análisis de siembra |
| `SIEMBRA_SIN_INDICADORES` | `55` | sin_indicadores en siembra |
| `SIEMBRA_SOSPECHOSOS` | `15` | sospechosos en siembra |
| `SIEMBRA_MALICIOSOS` | `30` | maliciosos en siembra |
| `SIEMBRA_SIN_MODELO` | `60` | resueltos por heurística |

## Invariants

1. **I1**: `AnalisisPersistido` nunca contiene clave `htmlBody`.
2. **I2**: `AnalisisPersistido` nunca contiene clave `contenido` en adjuntos.
3. **I3**: `Metricas.por_dia` tiene un elemento por cada día del rango (incluidos cero).
4. **I4**: Siembra ejecutada 2 veces deja exactamente 100 documentos con `origen="siembra"`.
5. **I5**: `tasa_falsos_positivos` es `None` si no hay documentos con `retroalimentacion`.
