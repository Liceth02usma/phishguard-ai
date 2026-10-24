# Data Model: Análisis y Expansión de URLs (fase 1)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

Entidades extraídas de FR-001..FR-007, del catálogo 5.2 de
`docs/PLAN_MODIFICACIONES_PHISHGUARD.md` y de las decisiones de research. Todas son
Pydantic (`mypy --strict`) o `Protocol` de puertos en `analisis_urls/puertos.py`.
`models.py` (EmailData) **no cambia** (research D3/D11).

## Constantes (catálogo y límites — Art. III.6)

| Constante | Valor | Fuente |
|---|---|---|
| `TOPE_SALTOS` | `5` | FR-003 / SC-003 (tabla M04b) |
| `TIMEOUT_URL_SEGUNDOS` | `5.0` | FR-003 / SC-003 (tabla M04b) |
| `UMBRAL_URL_LARGA` | `200` | FR-002 (`URL_LARGA`) / M04b |
| `DIAS_DOMINIO_NUEVO` | `30` | M04b ("dominio con menos de 30 días") |
| `REDES_PROHIBIDAS` | tuple de `ip_network`: `10/8`, `172.16/12`, `192.168/16`, `127/8`, `169.254/16`, `::1`, `fc00::/7`, `fe80::/10` | FR-004 literal |
| `CATALOGO_URL` | dict código → (severidad, puntos) con los 13 códigos de 5.2 | catálogo 5.2 |

**Catálogo 5.2 — 13 códigos** (solo los de URL; los `VT_*` son de la spec 006):

| Código | Severidad | Puntos |
|---|---|---|
| `URL_TEXTO_DISTINTO_DESTINO` | alta | 20 |
| `URL_HOST_IP` | alta | 15 |
| `URL_ACORTADA` | media | 10 |
| `URL_ARROBA` | media | 10 |
| `URL_PUNYCODE` | media | 10 |
| `URL_TLD_RIESGO` | baja | 5 |
| `URL_SUBDOMINIOS_EXCESIVOS` | baja | 5 |
| `URL_PUERTO_NO_ESTANDAR` | baja | 5 |
| `URL_HTTP_SIN_CIFRADO` | baja | 5 |
| `URL_LARGA` | baja | 3 |
| `URL_PARAMETROS_SENSIBLES` | media | 8 |
| `REDIRECCION_EXCESIVA` | media | 10 |
| `URL_DOMINIO_NUEVO` | alta | 15 |

`VT_URL_SOSPECHOSA`, `VT_DESCONOCIDO`, `VT_NO_DISPONIBLE` y `VT_PRESUPUESTO_AGOTADO`
son **fueran de alcance** (VI.1): su catálogo pertenece a la spec 006.

## Entidades

### `BanderaURL` (modelo local, research D3)

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `codigo` | `Literal[<13 códigos>]` | incluido en `CATALOGO_URL` | FR-002 |
| `severidad` | `Literal["baja", "media", "alta"]` | — | catálogo 5.2 |
| `puntos` | `int` (`ge=0`) | copia del catálogo | catálogo 5.2 |
| `detalle` | `str` | sin valores sensibles ni correos (D12); cita host/puerto/nombres de parámetro | FR-002 detalle |

Mismos campos que `BanderaActivada` de la spec 003 → 007 concatena ambas listas sin
adaptación (D3). Sin tope local: el tope global por correo lo unifica 007 `[VERIFICAR]`.

### `ResultadoExpansion` (resultado del FR-003/FR-004/FR-005)

| Campo | Tipo | Notas |
|---|---|---|
| `estado` | `Literal["no_acortadora", "reputacion_conocida", "expandida", "limite_saltos", "limite_tiempo", "bloqueada_ssrf", "esquema_no_permitido", "error_controlado"]` | transiciones abajo |
| `destino_final` | `str \| None` | solo con `expandida` (URL ya saneada, D12) |
| `saltos` | `int` (`ge=0`, `le=5`) | peticiones realizadas |
| `duracion_ms` | `int` (`ge=0`) | reloj inyectado (D15) |
| `motivo` | `str \| None` | para `error_controlado`/`bloqueada_ssrf` (sin PII) |

### `UrlAnalizada` (fila por URL tras FR-001/FR-002)

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `original` | `str` | URL tal cual aparece (conservar, FR-001) | FR-001 |
| `normalizada` | `str` | host minúsculas, sin fragmento, sin tracking | FR-001 |
| `host` | `str` | no vacío si parseable | FR-001 |
| `esquema` | `str` | `http`/`https`/otro detectado | FR-001 |
| `texto_mostrado` | `str` | `""` si no vino de un enlace | FR-001 |
| `es_acortadora` | `bool` | host ∈ `ConfigURLs.acortadores` | FR-003 |
| `url_saneada` | `str` | sin valores sensibles: **única** que sale a red (FR-007) | FR-007 |
| `expansion` | `ResultadoExpansion \| None` | `None` = no evaluada aún | FR-003 |
| `codigos` | `list[Literal[<13>]]` | códigos activados en ESTA URL | FR-002 |

Invariantes: `original` nunca se sobrescribe (FR-001 pide conservarla para el
reporte); `url_saneada` es la que se pasa al puerto HTTP/RDAP/VT.

### `ResultadoURLs` (salida pública de `analizar_urls`)

| Campo | Tipo | Notas |
|---|---|---|
| `urls` | `list[UrlAnalizada]` | deduplicadas **tras normalizar**, orden de aparición (FR-001) |
| `banderas` | `list[BanderaURL]` | agregadas de todas las URLs, sin duplicar `(codigo, url)`, orden estable |
| `estadisticas` | `EstadisticasURLs` | `{total, expandidas, bloqueadas_ssrf, sin_expansion}` |

Propiedad `todas_las_banderas` = `banderas` (para 007: concatena con las de cabecera
de 003).

### `EstadisticasURLs`

`total: int`, `expandidas: int`, `bloqueadas_ssrf: int`, `sin_expansion: int`
(invariante de verificación en pruebas: `expandidas + bloqueadas_ssrf + sin_expansion
== total` cuando todas fueron evaluadas).

### `ConfigURLs` (configuración inyectable, D8)

| Campo | Tipo | Default (source) |
|---|---|---|
| `acortadores` | `frozenset[str]` | `SHORTENERS` de `genetic_logic` (grounded) |
| `tlds_riesgo` | `frozenset[str]` | propuesta D8 `[VERIFICAR]` |
| `parametros_tracking` | `frozenset[str]` | propuesta D8 `[VERIFICAR]` |
| `parametros_sensibles` | `frozenset[str]` | los 7 de FR-007: `token`, `key`, `session`, `email`, `user`, `code`, `password` (extendible por env, D12) | FR-007 literal |
| `umbral_subdominios` | `int` (`ge=1`) | `4` propuesta D8 `[VERIFICAR]` |
| `tope_saltos` | `int` | `TOPE_SALTOS = 5` (fijo por FR-003; campo por testabilidad) |
| `timeout_url` | `float` | `TIMEOUT_URL_SEGUNDOS = 5.0` (ídem) |

Constructor `ConfigURLs.desde_entorno()` lee `ACORTADORES`, `TLD_RIESGO`,
`PARAMETROS_TRACKING`, `PARAMETROS_SENSIBLES`, `URL_SUBDOMINIOS_MAX` (listas
separadas por coma). Configuración inválida → `ConfiguracionError` (III.9).

### `DependenciasURLs` (puertos inyectados — D4/D5/D6/D7/D15)

| Campo | Protocol | Operación | Default prod |
|---|---|---|---|
| `resolvedor` | `ResolvedorDNS` | `resolver(host) -> list[IPv4Address \| IPv6Address]` | `socket.getaddrinfo` |
| `http` | `ClienteHTTPExpansion` | `solicitar(url) -> RespuestaRedireccion` | adapter `requests` (D6) |
| `cache` | `CacheReputacionURL` | `conoce(url_saneada) -> bool` | `CacheVacia` (D4) |
| `rdap` | `ClienteRDAP` | `antiguedad_dias(dominio) -> int \| None` | `SinRDAP` (D5) |
| `reloj` | `Callable[[], float]` | monotónico | `time.monotonic` (D15) |

`dependencias_por_defecto()` → cadena real (DNS real, `requests`, caché vacía, sin
RDAP, reloj real). Las pruebas inyectan dobles (`tests/unit/dobles_red.py`).

### `RespuestaRedireccion` (salida del puerto HTTP)

`status: int`, `location: str | None`, `ya_leido: bool` (invariante AC-URL-04: el
cliente nunca marca cuerpo leído; la prueba afirma `False` y que el servidor local
no observó lecturas).

## Reglas de validación (por FR)

- **FR-001**: candidatas de `href`/`src`/`action`/texto plano/texto de enlace; solo
  `http(s)` (un `mailto:` no es candidata); deduplicar **tras** normalizar; `original`
  intacta; entrada vacía → `urls=[]`, `banderas=[]` (sin error).
- **FR-002**: una bandera por regla pura; `codigo` obligatoriamente del catálogo;
  `puntos` copiados, no calculados; ninguna bandera activa por "presencia" de dato
  ausente (ej.: sin RDAP no hay `URL_DOMINIO_NUEVO` — D5).
- **FR-003**: solo `es_acortadora` y con caché vacía (D4) se expande; la expansión se
  evalúa sobre `url_saneada`.
- **FR-004**: toda IP resuelta de cada salto ∈ permitidas; bloqueada ⇒ 0 conexiones
  y `bloqueada_ssrf`.
- **FR-005**: sin evaluar JS; sin leer cuerpos (`RespuestaRedireccion.ya_leido`).
- **FR-006**: `cache.conoce(url_saneada)` ⇒ `estado = "reputacion_conocida"`, sin
  petición alguna.
- **FR-007**: `url_saneada` sin parámetros sensibles ni valores con forma de correo;
  es el único argumento que recibe el puerto HTTP.

## Transiciones de estado (máquina de `ResultadoExpansion`)

```text
[inicio]
   │ host ∉ acortadores ──────────────────────────────► no_acortadora (fin)
   │ caché VT conoce(url_saneada) ────────────────────► reputacion_conocida (fin)
   │ esquema ∉ {http, https} ─────────────────────────► esquema_no_permitido (fin)
   ▼
[expandiendo] saltos=0, t0=reloj
   │ reloj − t0 > 5 s ────────────────────────────────► limite_tiempo (fin, bandera)
   │ resolver(host) → IP bloqueada (FR-004) ──────────► bloqueada_ssrf (fin, 0 conexiones)
   │ error de conexión/timeout/4xx/5xx ───────────────► error_controlado (fin)
   │ respuesta sin Location / host destino no-acortador► expandida (fin)
   │ respuesta 3xx, saltos+1 < 5 ─────────────────────► [expandiendo] (salto++)
   │ respuesta 3xx, saltos+1 == 5 ────────────────────► limite_saltos (fin, bandera)
```

`limite_saltos` y `limite_tiempo` ⇒ bandera `REDIRECCION_EXCESIVA` (D9);
`bloqueada_ssrf` ⇒ 0 conexiones en esa URL (AC-URL-02).

## Relaciones

```text
EmailData (002, sin cambios)
   └── htmlBody + texto_limpio ──► motor.analizar_urls() ──► ResultadoURLs
                                      ├── ConfigURLs            (D8)
                                      └── DependenciasURLs      (D4–D7, D15)
ResultadoURLs
   ├── urls: [UrlAnalizada] ──► expansion?: ResultadoExpansion
   └── banderas: [BanderaURL] ──► catálogo 5.2 (constante)
```

Consumidores futuros (sin wiring aquí, D11): 006 consulta `urls[].url_saneada`; 007
concatena `banderas` con las de 003; 008 lee `ResultadoURLs` en su decisión.
