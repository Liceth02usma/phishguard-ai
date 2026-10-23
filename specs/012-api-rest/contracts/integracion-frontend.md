# Cómo integrar este contrato al frontend

**Para quién es**: desarrollador del frontend (React/TS u otro).  
**Objetivo**: tener **tipos + backend simulado en 3 comandos**, antes de que exista la API real (spec 012).  
**Archivos**: `openapi.yaml` (contrato máquina) · `api-rest.md` (contrato legible) · esta guía.

---

## Requisitos

- Node.js 18+ (`npx` no instala nada permanente).
- El `openapi.yaml` copiado al repo del frontend (hoy no hay frontend en este repo; cópialo o enlázalo por URL raw de git).

```
frontend/
└── api/
    └── openapi.yaml   ← copia de specs/012-api-rest/contracts/openapi.yaml
```

## Paso 0 — Verificar que el contrato está sano

```bash
npx @redocly/cli lint api/openapi.yaml
```

0 errores = listo para generar. (Opcional, ver en navegador: `npx redocly preview-docs api/openapi.yaml`.)

## Paso 1 — Generar los tipos TypeScript

```bash
npx openapi-typescript api/openapi.yaml -o src/api/schema.ts
```

Salen todos los tipos: `paths`, `components['schemas']['Analisis']`, `Veredicto`, `Metricas`… con autocompletado y errores en compilación si el backend cambia de forma.

## Paso 2 — Cliente HTTP tipado (~1 kB)

```bash
npm i openapi-fetch
```

```ts
// src/api/client.ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "X-API-Key": import.meta.env.VITE_API_KEY ?? "dev-key" }, // Art. V.8: una sola clave, sin roles
});
```

Uso en cualquier componente:

```ts
// Lista con filtros — data ya viene tipado
const { data, error } = await api.GET("/api/analyses", {
  params: { query: { veredicto: ["malicioso"], limite: 50, pagina: 1 } },
});

// Analizar (dry_run por defecto en el backend)
const { data: analisis } = await api.POST("/api/analyses", {
  body: { modo: "pegar", subject: "…", text: "…" },
});

// Métricas del tablero
const { data: m } = await api.GET("/api/metrics/summary", { params: { query: { rango: "7d" } } });
```

**Alternativa con hooks React Query de una**:  
`npx orval --input api/openapi.yaml --output src/api --client react-query` → genera `useQuery`/`useMutation` tipados.

## Paso 3 — Backend simulado mientras no existe la API

```bash
npx @stoplight/prism-cli mock api/openapi.yaml
# → http://127.0.0.1:4010 (devuelve los ejemplos del YAML y simula 401/422/429)
```

Cambia solo la URL base al usarlo:

```ts
baseUrl: "http://127.0.0.1:4010",   // mock Prism
// baseUrl: "http://localhost:8000", // API real cuando exista
```

Alternativa a nivel de navegador (más control por ruta): **MSW** con `@mswjs/openapi`, que genera los handlers desde el mismo YAML.

**Postman/Bruno** (para probar a mano): Import → File → `openapi.yaml`.

---

## Reglas del contrato que el front DEBE manejar

| # | Regla | Qué hacer en la UI |
|---|---|---|
| 1 | **201 no es "todo bien"**: VT/modelo/RDAP caídos devuelven 201 con `veredicto: "revision_manual"` y `verificaciones_incompletas[]` | Mostrar *"Revisión manual"* + aviso de verificación incompleta; **no** mostrar toast de error |
| 2 | Errores reales = envelope `{ error: { codigo, mensaje, detalles } }` | Un helper único que lee `error.codigo` (401 → pedir clave, 422 → resaltar campo, 429 → reintentar en 60 s, 503 → "servicio caído") |
| 3 | `dry_run` activo por defecto → `accion.simulada: true` | Etiqueta *"Simulado"* en la acción; solo mostrar acción real si el front envía `dry_run: false` |
| 4 | `GET /analyses` pagina (`limite` ≤ 50) | Paginador con tope 50 por página |
| 5 | 429 al 31er análisis en un minuto | Deshabilitar botón *"Analizar"* ~60 s |
| 6 | Export CSV es un archivo (`text/csv` con BOM) | Descargar como Blob; el prefijo `'` de protección ya viene aplicado — no "limpiarlo" |
| 7 | Sin roles (Art. V.8) | Un solo nivel de acceso: si hay `X-API-Key`, todo está habilitado (incluido `POST /jobs/gmail/run`) |
| 8 | Veredictos: 4 valores, `revision_manual` incluido | Colores/etiquetas para `malicioso`, `sospechoso`, `revision_manual` (*"Revisión manual"*), `sin_indicadores` |

## Cuando la API real exista (spec 012 implementada)

1. `baseUrl` → `http://localhost:8000` (o despliegue) manteniendo `X-API-Key`.
2. FastAPI servirá su propio `/docs`; comprobar que coincide con `openapi.yaml` — esa comparación **es** la prueba de contrato AC-API-04.
3. Si algo divergió, este YAML es la fuente: se actualiza el contrato primero y después el backend.

## Comandos resumen

```bash
npx @redocly/cli lint api/openapi.yaml                                  # 0) validar
npx openapi-typescript api/openapi.yaml -o src/api/schema.ts            # 1) tipos
npx @stoplight/prism-cli mock api/openapi.yaml                          # 2) mock en :4010
npx orval --input api/openapi.yaml --output src/api --client react-query  # (opcional) hooks
```

## Preguntas abiertas del contrato

Algunas formas están marcadas `[PROPUESTA]`/`[VERIFICAR]` en [api-rest.md](./api-rest.md) §7 (shape de `/samples`, paginación, nombres de campos). Si el frontend necesita cerrarlas ya, son decisiones de una línea — pídelas y se actualizan el YAML y el `.md` juntos (el YAML manda).
