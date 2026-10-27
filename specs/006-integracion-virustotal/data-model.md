# Data Model: Integración con VirusTotal API v3

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Tipos y constantes de `src/level2_agent/virustotal/`. Los valores numéricos son
**literales de M06.1–M06.4 / tabla 14.x / catálogos 5.2–5.3** (Art. VI.2); nada se
inventa.

## Constantes (nunca cadenas mágicas, Art. III.6)

| Constante | Valor | Fuente literal |
|---|---|---|
| `TOPE_RPM_PUBLIC` | 4 | M06.1 / M06.3 (4 solicitudes por minuto) |
| `TOPE_DIA_PUBLIC` | 500 | M06.1 / M06.3 (500 por día) |
| `REINTENTOS_MAX` | 3 | M06.3 ("hasta 3") |
| `ESPERA_BASE_SEGUNDOS` | 1 | M06.3 (1 s, 2 s, 4 s exponencial) |
| `FALLOS_CORTACIRCUITO` | 5 | FR-004 ("tras 5 fallos consecutivos") |
| `VENTANA_CORTACIRCUITO_SEGUNDOS` | 60 | FR-004 ("se abre 60 s") |
| `TTL_ARCHIVO_DIAS` | 7 | FR-005 ("archivos 7 días") |
| `TTL_URL_DIAS` | 1 (24 h) | FR-005 ("URLs, dominios e IPs 24 horas") |
| `TTL_DESCONOCIDO_HORAS` | 1 | FR-005 (""desconocido" 1 hora") |
| `MAX_CONSULTAS_POR_CORREO` | 10 (default env) | FR-006 / tabla 14.x `VT_MAX_POR_CORREO` |
| `TIMEOUT_CONEXION_SEGUNDOS` | 3.0 | M06.3 ("conexión 3 s") |
| `TIMEOUT_LECTURA_SEGUNDOS` | 10.0 | M06.3 ("lectura 10 s") |
| `BASE_VT` | `https://www.virustotal.com/api/v3` | M06.2 |
| `ESPERA_ANALISIS_URL_SEGUNDOS` | 5 (máx. 3 consultas) | M06.2 (`POST /urls` + `GET /analyses/{id}`) |
| `UMBRAL_MALICIOSA` (env `VT_UMBRAL_MALICIOSA`) | 3 | M06.4 / FR-007 |
| `UMBRAL_SOSPECHOSA` (env `VT_UMBRAL_SOSPECHOSA`) | 3 | M06.4 / FR-007 |
| `UMBRAL_LIMPIA` (env `VT_UMBRAL_LIMPIA`) | 20 | M06.4 / FR-007 (`harmless + undetected >= 20`) |

## Catálogo VT (códigos propios de la 006; catálogos 5.2/5.3)

Los códigos `VT_*` fueron **excluidos** del catálogo 5.2 de la spec 004 y del 5.3 de
la spec 005 — les pertenecen a esta spec (Art. VI.2, fuente única):

| Código | Severidad | Puntos | Efecto |
|---|---|---|---|
| `VT_URL_SOSPECHOSA` | alta | 20 | URL clasificada `sospechosa` (catálogo 5.2) |
| `VT_ADJ_SOSPECHOSO` | alta | 25 | Hash de adjunto clasificado `sospechosa`/`maliciosa` (catálogo 5.3) |
| `VT_DESCONOCIDO` | informativa | 0 | 404/error/cuota → `desconocida`; **obliga a `revision_manual`** si la verificación era obligatoria |
| `VT_NO_DISPONIBLE` | informativa | 0 | Cortacircuitos abierto / VT caído; **obliga a `revision_manual`** |
| `VT_PRESUPUESTO_AGOTADO` | informativa | 0 | Exceso sobre `VT_MAX_POR_CORREO`; **obliga a `revision_manual`** |

`puntos`/`severidad` se **copian** del catálogo (`CATALOGO_VT` es la transcripción
literal), nunca se calculan.

> Decisión de interpretación (documentada, no inventada): `VT_ADJ_SOSPECHOSO` cubre la
> consulta de hash de adjunto con veredicto `sospechosa` **o** `maliciosa` (la fila
> "regla dura M09" del M06.4 no define código propio; la decisión de veredicto es de
> la spec 008). `VT_URL_SOSPECHOSA` cubre URL `sospechosa`; la URL `maliciosa` alimenta
> directamente la regla dura de 008 vía `ResultadoVT.clasificacion` sin flag de puntos
> (misma lógica: los puntos ya no aportan, la regla dura manda).

## Tipos Pydantic / dataclass

### `LastAnalysisStats` (Pydantic, entrada del clasificador)

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `malicious` | `int` | `ge=0` | `data.attributes.last_analysis_stats` (M06.4) |
| `suspicious` | `int` | `ge=0` | idem |
| `harmless` | `int` | `ge=0` | idem |
| `undetected` | `int` | `ge=0` | idem |

`timeout`/`failure` no participan en la tabla (M06.4 no los usa); se descartan al
parsear. Campos faltantes → se tratan como 0 y, si **todos** faltan, el cliente no
llega a `clasificar_stats` (→ `desconocida` por sin datos).

### `Clasificacion` (Literal)

`Literal["maliciosa", "sospechosa", "limpia", "desconocida"]` — valores literales de
M06.4. `desconocida` cubre: 404, error de transporte, cuota agotada, cortacircuitos
abierto, caché vencida sin respuesta, respuesta sin `last_analysis_stats`.

### `BanderaVT` (Pydantic, shape compatible con 003/004/005 → concatenable en 007)

| Campo | Tipo | Validación |
|---|---|---|
| `codigo` | `str` | ∈ `CATALOGO_VT` (5 códigos) |
| `severidad` | `Literal["media", "alta", "informativa"]` | copiada del catálogo |
| `puntos` | `int` | `ge=0`, copiado del catálogo |
| `detalle` | `str` | no vacío; cita tipo + identificador **saneado**/host, jamás la URL original con parámetros, la clave ni PII (Art. V.4, AC-VT-07) |

### `ResultadoVT` (Pydantic, salida pública por consulta)

| Campo | Tipo | Validación / semántica |
|---|---|---|
| `tipo` | `Literal["archivo", "url", "dominio", "ip"]` | tipo de indicador consultado |
| `identificador` | `str` | SHA-256 hex64 / URL Base64 url-safe sin relleno / dominio / IP |
| `clasificacion` | `Clasificacion` | salida de `clasificar_stats` o `desconocida` |
| `fuente` | `Literal["red", "cache", "sin_llamada"]` | `sin_llamada` = presupuesto/cuota/cortacircuitos (transparencia para 008) |
| `banderas` | `list[BanderaVT]` | 0..n; orden según `CATALOGO_VT`; códigos únicos |
| `stats` | `LastAnalysisStats \| None` | `None` si no hubo datos (404/error) |
| `consultas_externas` | `int` | `ge=0` `le=1`; 0 si fue caché/presupuesto (nunca consume ficha) |

**Invariantes**: (IV1) `clasificacion == "limpia"` solo si `fuente ∈ {red, cache}` con
stats completos; (IV2) `fuente == "sin_llamada"` ⇒ `clasificacion == "desconocida"`;
(IV3) jamás excepción por datos de entrada — todo error se modela en estos campos
(III.9 + AC-VT-01/05); (IV4) la misma entrada + mismas respuestas → mismo
`ResultadoVT` (orden estable, D15).

### `EntradaCache` (dataclass inmutable, serializer a Mongo)

| Campo | Tipo | Semántica |
|---|---|---|
| `clave` | `str` | `"{tipo}:{identificador}"` (M06.3: "clave = tipo + identificador") |
| `clasificacion` | `Clasificacion` | clasificación precalculada |
| `stats` | `LastAnalysisStats \| None` | para re-clasificar si cambian umbrales sin reconsultar |
| `guardada_en` | `datetime` (UTC) | reloj inyectado |
| `expira_en` | `datetime` (UTC) | `guardada_en + TTL` según tipo (7 d / 24 h / 1 h) — índice TTL de Mongo |

### `Presupuesto` (dataclass, por correo — FR-006)

| Campo | Tipo | Semántica |
|---|---|---|
| `restantes` | `int` | inicia en `VT_MAX_POR_CORREO` (default 10) |
| `usar() -> bool` | método | atómico: si `restantes > 0` resta 1 y devuelve `True`; si no, `False` |
| `agotado` | property | `restantes == 0` |

**Orden de consumo de prioridad** (M06.3 literal, contrato del wiring futuro):
hashes → URLs con banderas de riesgo (media/alta de la 004) → dominios → IPs →
demás URLs. Golpes de caché no lo invocan.

### `ConfigVT` (Pydantic-settings manual vía `os.getenv`)

| Campo | Env | Default | Validación |
|---|---|---|---|
| `tier` | `VT_TIER` | `public` | ∈ {`public`, `premium`} si no → `ConfiguracionError` |
| `rpm` | `VT_RPM` | 4 | `ge=1` |
| `tope_dia` | `VT_DAILY` | 500 | `ge=0` (0 = sin tope) |
| `max_por_correo` | `VT_MAX_POR_CORREO` | 10 | `ge=1` |
| `upload_unknown` | `VT_UPLOAD_UNKNOWN` | `False` | Art. V.6 |
| `submit_unknown_urls` | `VT_SUBMIT_UNKNOWN_URLS` | `False` | Art. V.6 |
| `umbral_maliciosa` | `VT_UMBRAL_MALICIOSA` | 3 | `ge=1` |
| `umbral_sospechosa` | `VT_UMBRAL_SOSPECHOSA` | 3 | `ge=1` |
| `umbral_limpia` | `VT_UMBRAL_LIMPIA` | 20 | `ge=0` |
| `api_key` | `VT_API_KEY` | — | **no se persiste ni se loguea**; ausente ⇒ consultas ⇒ `VT_NO_DISPONIBLE` (sin clave no se intenta red) |

Booleans env: `"true"/"1"/"yes"` → True (case-insensitive); todo lo demás → False.

## Modelos externos consumidos (sin cambios)

| Modelo | De | Campos que 006 lee |
|---|---|---|
| `EmailData` | spec 002 (`models.py`) | `urls` (para futuro wiring), no se modifica |
| `Adjunto` | spec 002 | `sha256` (hash a consultar) |
| `AnalisisAdjunto` | spec 005 | `sha256` (lo que produce `analizar_adjunto`) |
| `ResultadoURLs` | spec 004 | `urls[].url_saneada` y `urls[].codigos` (prioridad 2 y saneado, D7/D8) |

006 **no** importa `EmailData` en su núcleo: el cliente trabaja sobre indicadores ya
extraídos (hash/URL/dominio/IP); la consulta "por correo" (presupuesto) recibe listas
de indicadores, no el `EmailData` — mantiene 006 independiente y testeable (D14).

## Persistencia (MongoDB)

| Colección | Documento | Índice | TTL |
|---|---|---|---|
| `vt_cache` | `EntradaCache` serializada | `_id = clave`; `expira_en` con `expireAfterSeconds=0` | por tipo: 7 d / 24 h / 1 h (FR-005) |
| `vt_contador` | `{_id: "YYYY-MM-DD", usos: int}` | `_id` | el documento del día previo expira por TTL de 48 h (o se ignora por clave de día — decisión de implementación: **clave de día + TTL 48 h**) |

`_id` con la clave/`dia` da atomicidad (`$inc` para el contador diario ⇒ 500/día
correcto bajo concurrencia; AC-VT-03 "tras un reinicio" se prueba con dos instancias de
la caché/contador en memoria distintas apuntando al mismo almacén de prueba).

## Máquina de estados del cortacircuitos (FR-004, Art. II.2 transición de estados)

```
        5 fallos consecutivos            ventana (60 s) vencida
cerrado ──────────────────────▶ abierto ─────────────────────────▶ cerrado
   ▲                             │  no se llama:                    │
   │  respuesta 200 o 404        │  desconocida + VT_NO_DISPONIBLE  │
   └─────────────────────────────┘◀─────────────────────────────────┘
        (cualquier resultado concluyente reinicia el contador de fallos)
```

- Fallo = error de transporte, 5xx, o 429 tras agotar reintentos.
- 200 y 404 son **resultados** (reinician fallos); los demás 4xx (400/401/403) también
  son terminales sin reintento (M06.3) ⇒ reinician.
- Reloj inyectado: las transiciones se prueban con 59/60/61 s (valores límite).
