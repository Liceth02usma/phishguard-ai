# Contract: API REST para el Frontend

**Spec**: [spec.md](../spec.md) (FR-001 a FR-007) | **Máquina**: [openapi.yaml](./openapi.yaml) | **Guía front**: [integracion-frontend.md](./integracion-frontend.md)

**Fuentes**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` §14.2 (documento), §14.3 (endpoints) y §14.4 (errores); specs 011 y 012; `src/level2_agent/models.py`; constitución Art. V.8.

**Fecha**: 2026-10-22 · **Estado**: contrato inicial (frontend puede arrancar con mocks)

---

## 1. Generalidades

| Regla | Detalle |
|---|---|
| Base | `/api`, respuestas `application/json; charset=utf-8` |
| Autenticación | Cabecera `X-API-Key` en **todos** los endpoints salvo `GET /api/health` (AC-API-07 → 401) |
| Roles | **No existen** (constitución Art. V.8): una única clave compartida; `POST /jobs/gmail/run` no exige nada más que la clave |
| `dry_run` | Activo **por defecto** en `POST /analyses`; la respuesta lo refleja en `accion.simulada = true` (AC-API-03) |
| Límite de tasa | 30 análisis por minuto por clave e IP; el análisis 31 → 429 (AC-API-09) |
| Degradación | Caída de VirusTotal, el modelo o RDAP **no es error**: → **201** con `veredicto = revision_manual` + `verificaciones_incompletas` (AC-API-10) |
| CORS / cabeceras | Solo orígenes de `CORS_ORIGINS`; cabeceras de seguridad (FR-003) |
| PII | `correo.asunto` y `correo.cuerpo_enmascarado` siempre enmascarados; nunca hay HTML original ni contenido de adjuntos |

## 2. Enums compartidos (tipos TS del front)

| Enum | Valores |
|---|---|
| `Veredicto` | `malicioso` · `sospechoso` · `revision_manual` · `sin_indicadores` |
| `Severidad` | `Crítico` · `Alto` · `Medio` · `Bajo` |
| `Ruta` | `reglas` · `heuristica` · `ia` |
| `Modo` | `pegar` · `eml` · `muestra` · `gmail` |
| `Origen` | `gmail` · `api` · `seed` |
| `Reputacion` | `maliciosa` · `sospechosa` · `limpia` · `desconocida` (404/error de VT → `desconocida`, nunca `limpia`) |
| `Feedback` | `confirmado` · `falso_positivo` |
| `Rango` | `7d` · `30d` · `90d` |
| `AuthResult` (spf/dkim/dmarc) | tokens RFC 8601 (`pass`, `fail`, `none`, …) y `desconocido` sin evaluación confiable [VERIFICAR] |

## 3. Documento `analyses` (la respuesta estándar)

Es lo que devuelven `POST /analyses`, `GET /analyses/{id}`, y lo que contiene `items[]` en la lista (§14.2):

```json
{
  "id": "65f1c0ffee00000000000421",
  "origen": "api",
  "modo": "pegar",
  "creado_en": "2026-10-22T14:03:11-05:00",
  "duracion_ms": 4200,
  "correo": {
    "remitente": "b***@banc0-seguro.com",
    "asunto": "Acceso bloqueado: verifica tu cuenta",
    "cuerpo_enmascarado": "Tu cuenta será suspendida en 24 h. Ingresa aquí: [NÚMERO_OCULTO]"
  },
  "resultado": {
    "score": 82,
    "score_genetico": 61,
    "ruta": "reglas",
    "es_phishing": true,
    "veredicto": "malicioso",
    "nivel_severidad": "Crítico",
    "resumen": "Correo de suplantación con urgencia y enlace acortado.",
    "analisis_tecnico": "SPF falla; dominio parecido a la marca protegida; URL acortada.",
    "justificacion_veredicto": "Regla R2 (URL maliciosa) y R4 (autenticación fallida).",
    "indicadores": [{ "codigo": "urgencia", "descripcion": "Urgencia", "peso": 1.25 }],
    "banderas": [
      { "codigo": "SPF_FALLA", "severidad": "alta", "puntos": 15, "detalle": "spf=fail del servidor propio" },
      { "codigo": "DOMINIO_PARECIDO", "severidad": "alta", "puntos": 15, "detalle": "banc0-seguro.com ~ banco.com" }
    ],
    "reglas_aplicadas": ["R2", "R4"],
    "verificaciones_incompletas": [],
    "autenticacion": { "spf": "fail", "dkim": "desconocido", "dmarc": "desconocido" },
    "urls": [
      { "url": "http://bit.ly/x", "reputacion": "maliciosa", "detalle_vt": { "malicious": 7, "suspicious": 1 } }
    ],
    "adjuntos": [
      { "nombre": "factura.pdf.exe", "tipo_real": "application/x-dosexec",
        "sha256": "e3b0…b855", "tamano": 123456, "reputacion": "maliciosa" }
    ],
    "version_pesos": "pesos_v1",
    "version_modelo": "models/gemini-2.5-flash-lite",
    "ticket": { "clave": "SEC-12", "url": "https://proyecto.atlassian.net/browse/SEC-12" }
  },
  "accion": { "ejecutada": "etiqueta_phishing", "simulada": true },
  "retroalimentacion": null
}
```

Notas para el front:

- **`revision_manual` es un veredicto más** (FR-007): mostrarlo como *"Revisión manual"* (§14.5).
- `verificaciones_incompletas[]` no vacío ⇒ el backend degradó (VT/modelo/RDAP caído); el veredicto será `revision_manual`, **no** es un error HTTP.
- `es_phishing` es el campo legado; el canónico para UI es `veredicto`.
- `banderas` suma ≤ 60 puntos por correo (spec 003).

## 4. Endpoints (12)

| # | Método y ruta | Recibe | Devuelve | Códigos |
|---|---|---|---|---|
| 1 | `GET /api/health` | — (sin clave) | `{ estado: "ok" \| "error" }` | 200, 503 |
| 2 | `GET /api/integraciones` | — | estado Mongo, VT (modo + cuota), modelo, Gmail — **sin claves ni URLs** | 200, 401, 503 |
| 3 | `GET /api/samples` | — | `Muestra[]` (`id`, `nombre`, `descripcion`, `contenido`) [PROPUESTA] | 200, 401 |
| 4 | `POST /api/analyses` | JSON (`pegar`/`muestra`) o multipart (`eml`) | `Analisis` (§3) con `accion.simulada` | **201**, 401, 413, 422, 429, 500, 503 |
| 5 | `GET /api/analyses` | query: `veredicto`[], `severidad`[], `q`, `desde`, `hasta`, `orden`, `pagina`, `limite`≤50 | `{ items: Analisis[], pagina, limite, total }` [PROPUESTA] | 200, 401, 422 |
| 6 | `GET /api/analyses/export.csv` | mismos filtros (subset) | `text/csv` (BOM, escape, ≤5000 filas) | 200, 401 |
| 7 | `GET /api/analyses/{id}` | path `id` | `Analisis` | 200, 401, 404 |
| 8 | `PATCH /api/analyses/{id}/feedback` | `{ "feedback": "confirmado" \| "falso_positivo" }` | `Analisis` actualizado [PROPUESTA] | 200, 401, 404, 422 |
| 9 | `DELETE /api/analyses/{id}` | — | vacío (borra análisis + su caché) | 204 [VERIFICAR], 401, 404 |
| 10 | `GET /api/metrics/summary?rango=7d\|30d\|90d` | query `rango` (obligatorio) | `Metricas` (§6) | 200, 401, 422 |
| 11 | `GET /api/jobs/gmail` | — | `{ ultimo_ciclo, pendientes, fallidos }` | 200, 401 |
| 12 | `POST /api/jobs/gmail/run` | — (misma clave, **sin roles**) | estado del poller tras el ciclo [PROPUESTA] | 200, 401, 429 |

### 4.1 `POST /api/analyses` — los 3 modos

**Modo `pegar` (JSON)** — campos alineados con `normalizar_desde_api()` (spec 002):

```json
{
  "modo": "pegar",
  "dry_run": true,
  "from": "j***@empresa.com",
  "subject": "Acceso bloqueado",
  "text": "Tu cuenta será suspendida…",
  "headers": { "Authentication-Results": "mx.propio; spf=fail dkim=none dmarc=none" }
}
```

Campos opcionales: `raw` (MIME completo en base64 url-safe — con él se ignora el resto), `html`, `to`, `message_id`.

**Modo `muestra` (JSON)**:

```json
{ "modo": "muestra", "muestra": "malicious", "dry_run": true }
```

**Modo `eml` (multipart/form-data)**: campo `archivo` (`.eml`, `message/rfc822`) + `dry_run`. Más de 25 MB → **413**. La respuesta incluye `adjuntos[]` con `sha256` y `reputacion` (AC-API-02).

**Respuesta 201**: el documento `Analisis` de §3. Si algo externo falló: **201 igual**, con `veredicto: "revision_manual"` y `verificaciones_incompletas` poblado (AC-API-10).

### 4.2 Lista y exportación

- `GET /api/analyses` — filtros combinables; `veredicto` y `severidad` son **repetibles** (`?veredicto=malicioso&veredicto=sospechoso`); `limite` máximo 50 (422 si se excede).
- `GET /api/analyses/export.csv` — mismos filtros; CSV **UTF-8 con BOM**; toda celda que empiece con `=`, `+`, `-` o `@` lleva prefijo `'` (asunto `=HYPERLINK(...)` no se ejecuta); **máximo 5 000 filas** (5 001 resultados → 5 000) (AC-API-08).

## 5. Errores

Envelope uniforme (FR-002):

```json
{ "error": { "codigo": "NO_AUTENTICADO", "mensaje": "Falta o es inválida la cabecera X-API-Key.", "detalles": null } }
```

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTENTICADO` | Falta o es inválida la `X-API-Key` (todo salvo health) |
| 404 | `NO_ENCONTRADO` | Análisis inexistente |
| 413 | `ENTRADA_GRANDE` | Multipart > 25 MB |
| 422 | `VALIDACION` | Falla Pydantic (entrada malformada) |
| 429 | `DEMASIADAS_SOLICITUDES` | 30 análisis en un minuto |
| 500 | `ERROR_INTERNO` | Error no controlado |
| 503 | `SERVICIO_NO_DISPONIBLE` | Mongo caído |

> **Regla de oro para el front**: VT/modelo/RDAP caídos → **201 con `revision_manual`**, nunca 5xx. Un 5xx es solo problema real del servidor o de Mongo.

## 6. `GET /metrics/summary` (§14.3 + spec 011 FR-004)

```json
{
  "rango": "7d",
  "total": 100,
  "por_veredicto": { "sin_indicadores": 55, "sospechoso": 15, "malicioso": 30, "revision_manual": 0 },
  "por_ruta": { "reglas": 20, "heuristica": 40, "ia": 40 },
  "pct_sin_modelo": 60.0,
  "duracion_media_ms": 4200,
  "por_dia": [ { "fecha": "2026-10-16", "total": 0 }, { "fecha": "2026-10-17", "total": 14 } ],
  "indicadores_frecuentes": [ { "codigo": "urgencia", "descripcion": "Urgencia", "frecuencia": 42 } ],
  "tasa_falsos_positivos": null,
  "consultas_vt": 812,
  "aciertos_cache_pct": 47.5,
  "revision_manual_total": 0
}
```

Invariantes que las pruebas del front pueden usar (datos de siembra, AC-PER-03/04/05):

- `total = 100`; `por_veredicto` = 55 / 15 / 30; `pct_sin_modelo = 60.0`
- `por_dia` tiene **un elemento por día del rango, incluidos los de cero**, en America/Bogota
- `tasa_falsos_positivos` es `null` sin retroalimentación

## 7. Marcas del contrato

| Marca | Item | Qué falta cerrar |
|---|---|---|
| [PROPUESTA] | `GET /samples` (forma de `Muestra`) | `ESPECIFICACION_INTERFAZ_PHISHING.md` v2.0 no está en el repo |
| [PROPUESTA] | Envoltorio de paginación `{items, pagina, limite, total}` | la spec no fija la forma |
| [PROPUESTA] | Campo `muestra` del modo muestra; campo `feedback` del PATCH | nombres no fijados |
| [PROPUESTA] | Respuesta de `POST /jobs/gmail/run` | no fijada |
| [VERIFICAR] | `DELETE` → 204 vs 200 | no fijado por la spec |
| [VERIFICAR] | Catálogo exacto de `AuthResult` y severidad de banderas | depende de specs 003 |
| [VERIFICAR] | Nombre de la variable de entorno de la clave (`X-API-Key`) | lo define spec 014 |
| [VERIFICAR] | Formato de `desde`/`hasta`/`orden`; defecto de `limite` | lo define el plan de la spec 012 |

## 8. Relación con la constitución

- **Art. V.8**: una única `X-API-Key`; sin roles (`POST /jobs/gmail/run` no tiene restricción extra).
- **Art. V.2**: `dry_run` por defecto; la acción externa real requiere envío explícito.
- **Art. V.4**: todo persistido y devuelto va enmascarado; sin HTML original.
- **Art. VI.2**: lo no fijado por la spec/plan queda marcado [PROPUESTA]/[VERIFICAR], nunca inventado en silencio.
