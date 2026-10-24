# Data Model: Análisis Estático de Adjuntos

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Investigación**: [research.md](./research.md)

Modelos de datos del paquete `src/level2_agent/adjuntos/`. Todo es Pydantic (Art. III.4)
salvo los objetos internos de contexto, que son `dataclass(frozen=True)` como en
`normalizacion/limites.py` (solo memoria, no forman parte del contrato público).

## Catálogo 5.3 (fuente única de verdad)

Constante `CATALOGO_ADJUNTOS` en `modelos.py`: `dict[codigo, (severidad, puntos)]`,
transcripción literal de la sección 5.3 de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`
(Art. VI.2: el código no admite puntos propios). Las banderas de esta spec son las 9
códigos `ADJ_*`; `VT_ADJ_SOSPECHOSO` pertenece a la spec 006 (veredicto de VirusTotal
sobre el hash) y **no** se emite aquí: queda documentada en el catálogo solo como
referencia del consumidor.

| Código | Severidad | Puntos | Detector (módulo) |
|---|---|---|---|
| `ADJ_EXTENSION_RIESGO` | alta | 20 | `extensiones.py` |
| `ADJ_DOBLE_EXTENSION` | alta | 20 | `extensiones.py` |
| `ADJ_TIPO_NO_COINCIDE` | alta | 15 | `firma.py` |
| `ADJ_MACRO` | alta | 20 | `office.py` |
| `ADJ_ENLACE_EXTERNO` | media | 10 | `office.py` |
| `ADJ_PDF_ACTIVO` | media | 10 | `pdf.py` |
| `ADJ_CIFRADO` | media | 12 | `comprimidos.py` |
| `ADJ_ARCHIVO_SOSPECHOSO` | alta | 15 | `pdf.py`, `comprimidos.py`, `office.py` (degradación) |
| `ADJ_HTML` | media | 10 | `extensiones.py` |

Constantes de umbral (Art. III.6): `ADJ_LIMITE_ENTRADAS_ZIP = 100`,
`ADJ_LIMITE_DESCOMPRIMIDO_ZIP = 100 * 1024 * 1024` (100 MiB; misma interpretación
MB = MiB que `LIMITE_BYTES_CORREO` de la spec 002), `ADJ_RATIO_MAXIMO_ZIP = 100`,
`EXTENSIONES_RIESGO_DEFAULT`, `EXTENSIONES_HTML_DEFAULT`,
`EXTENSIONES_DOCUMENTAL_DEFAULT` (D4/D8/D10).

## Entidades públicas

### `BanderaAdjunto` (Pydantic)

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `codigo` | `str` | debe ser clave de `CATALOGO_ADJUNTOS` | detector que la activa |
| `severidad` | `Literal["media","alta"]` | copia del catálogo | catálogo (D13) |
| `puntos` | `int` | `ge=0`; copia del catálogo | catálogo |
| `detalle` | `str` | no vacío; describe extensiones, tipos y hechos, **sin** nombres de archivo completos ni direcciones de correo (V.4) | detector |

Invariantes: sin dos entradas con el mismo `codigo` en una `AnalisisAdjunto`;
`severidad`/`puntos` siempre coinciden con el catálogo (el motor los rellena desde la
constante: un detector solo aporta `codigo` + `detalle`).

### `AnalisisAdjunto` (Pydantic) — salida de `analizar_adjunto`

| Campo | Tipo | Validación |
|---|---|---|
| `nombre` | `str` | el nombre original del adjunto (solo en memoria; nunca se usa para abrir archivos) |
| `tipo_declarado` | `str` | `Content-Type` declarado por la parte MIME (puede ser vacío) |
| `tipo_real` | `str` | familia detectada por firma (`filetype`) o `"desconocido"` si no hay firma concluyente (D5) |
| `tamano_bytes` | `int` | `ge=0`; longitud del payload |
| `sha256` | `str` | `pattern=r"^[0-9a-f]{64}$"` (FR-001: hash principal) |
| `md5` | `str` | `pattern=r"^[0-9a-f]{32}$"` (informativo) |
| `sha1` | `str` | `pattern=r"^[0-9a-f]{40}$"` (informativo) |
| `banderas` | `list[BanderaAdjunto]` | orden estable = orden del catálogo 5.3; sin códigos repetidos |
| `detalles` | `list[str]` | observaciones de degradación (p. ej. "pdf no parseable"); sin nombres completos |

Invariante fuerte: para **cualquier** entrada (vacía, truncada, nombre con `..` o
rutas), `analizar_adjunto` devuelve una `AnalisisAdjunto` con los tres hashes
correctos y sin excepción (AC-ADJ-06, D14).

### `ConfigAdjuntos` (Pydantic) — inyectado o `desde_entorno()`

| Campo | Tipo | Env | Default |
|---|---|---|---|
| `extensiones_riesgo` | `frozenset[str]` | `ADJ_EXTENSIONES_RIESGO` | `exe,scr,com,msi,dll,js,vbs,ps1,bat,cmd,hta,wsf,lnk,iso,img,vhd` (textual del M05) |
| `extensiones_html` | `frozenset[str]` | `ADJ_EXTENSIONES_HTML` | `html,htm,svg` |
| `extensiones_documental` | `frozenset[str]` | `ADJ_EXTENSIONES_DOCUMENTO` | `pdf,doc,docx,xls,xlsx,ppt,pptx,odt,ods,odp,txt,csv,jpg,jpeg,png,gif` (diseño documentado, D4) |
| `limite_entradas_zip` | `int` | `ADJ_LIMITE_ENTRADAS_ZIP` | `100` |
| `limite_descomprimido_zip` | `int` | `ADJ_LIMITE_DESCOMPRIMIDO_ZIP` | `104857600` (100 MiB) |
| `ratio_maximo_zip` | `int` | `ADJ_RATIO_MAXIMO_ZIP` | `100` |

Validación: extensiones normalizadas a minúsculas sin punto inicial; enteros `gt=0`;
entrada inválida → `ConfiguracionError` al construir (fail-fast, III.9). Las pruebas
unitarias construyen `ConfigAdjuntos` directamente, sin tocar el env (II.5).

## Objetos internos (dataclass frozen, no contrato)

### `ContextoAdjunto`

Transporta lo que todo detector necesita: `nombre: str`, `extension_final: str`,
`extensiones_previas: tuple[str, ...]`, `tipo_real: str`, `tipo_declarado: str`,
`payload: bytes`, `config: ConfigAdjuntos`. El motor lo construye **una vez** y lo
comparte; ningún detector recibe el `Message` MIME ni toca `models.py`.

### `ResultadoDetector`

`banderas: tuple[BanderaAdjunto, ...]` + `detalles: tuple[str, ...]`. Un detector
que falla devuelve `ResultadoDetector` con `ADJ_ARCHIVO_SOSPECHOSO` y su detalle
(D14), nunca lanza.

## Relaciones

```
analizar_adjunto(nombre, tipo_declarado, payload, config)
  └─ motor.py: construye ContextoAdjunto y ejecuta el registry ordenado
       ├─ hashes.py       ──▶ sha256 + md5 + sha1 (siempre, sin flag)      (FR-001)
       ├─ firma.py        ──▶ tipo_real + BanderaAdjunto (1 código)        (FR-002)
       ├─ extensiones.py  ──▶ BanderaAdjunto (hasta 3 códigos)             (FR-003)
       ├─ office.py       ──▶ BanderaAdjunto (2 códigos)  [Adapter olevba] (FR-004)
       ├─ pdf.py          ──▶ BanderaAdjunto (1 código + degradación)      (FR-004)
       └─ comprimidos.py  ──▶ BanderaAdjunto (2 códigos, con aborto)       (FR-005)
  ── motor deduplica, ordena por catálogo y rellena severidad/puntos ──▶ AnalisisAdjunto
```

`Adjunto` (spec 002, `models.py`) es la fuente de `nombre`, `tipo_declarado` y
`tamano_bytes`; los `payload` en bytes llegan de `CorreoBruto.adjuntos_crudos`
durante la normalización — esta spec **no** modifica `models.py` ni la cadena de
normalización (D15): el llamador que las specs 006/008 monten es quien cose
`Adjunto` + `AnalisisAdjunto` (por `nombre`/`sha256`).

## Máquina de estados (zip, la única con aborto)

```
inspeccionando ──¿cifrado?──▶ ADJ_CIFRADO (sigue listando metadatos, no lee contenido)
       │
       ├─ entradas > 100 ─────────────┐
       ├─ acumulado > 100 MiB ────────┼──▶ ABORTO + ADJ_ARCHIVO_SOSPECHOSO
       ├─ relación real > 100:1 ──────┤    (sin agotar memoria: streaming con tope)
       └─ ZipFile inválido ───────────┘
```

Los checks se hacen **durante** la lectura por bloques (no sobre los tamaños
declarados: D8), de forma que el aborto ocurre antes de materializar el exceso.

## Tabla de decisión (extensión × firma × content-type → banderas)

Resumen de la tabla completa que implementa `extensiones.py` + `firma.py`
(testeada fila a fila en `test_extensiones.py`):

| # | Ext final | Extensiones previas | Firma (filetype) | Content-Type | Banderas |
|---|---|---|---|---|---|
| 1 | `.pdf` | — | pdf | `application/pdf` | (ninguna) |
| 2 | `.pdf` | — | exe | `application/pdf` | `ADJ_TIPO_NO_COINCIDE` |
| 3 | `.exe` | — | exe | `application/octet-stream` | `ADJ_EXTENSION_RIESGO` |
| 4 | `.pdf.exe` | pdf | exe | — | `ADJ_EXTENSION_RIESGO` + `ADJ_DOBLE_EXTENSION` |
| 5 | `.exe ` (espacio antes de la ext) | — | — | — | `ADJ_DOBLE_EXTENSION` |
| 6 | `.html` | — | — | `text/html` | `ADJ_HTML` |
| 7 | `.svg` | — | — | `image/svg+xml` | `ADJ_HTML` |
| 8 | `.lnk` | — | desconocida | — | `ADJ_EXTENSION_RIESGO` |
| 9 | `.txt` | — | desconocida | `text/plain` | (ninguna) |
| 10 | `.docx` | — | zip (OOXML) | `application/vnd...` | (ninguna; office.py decide macro/enlace) |
| 11 | `.jpg.exe` | jpg | exe | — | `ADJ_EXTENSION_RIESGO` + `ADJ_DOBLE_EXTENSION` |
| 12 | `.pdf` | — | zip | `application/zip` | `ADJ_TIPO_NO_COINCIDE` |

## Validaciones cruzadas (tests del modelo)

1. Toda bandera activada pertenece al catálogo y sus `puntos`/`severidad` coinciden.
2. Sin códigos repetidos; orden estable igual al orden del catálogo 5.3.
3. `sha256`/`md5`/`sha1` siempre en formato hexadecimal válido, incluso para payload
   vacío (hash del vacío publicado).
4. `detalles` sin nombres de archivo completos (regex de prueba sobre todos los
   detalles producidos por los fixtures: no empiezan con el `nombre` del adjunto).
5. Propiedad (hypothesis): para bytes y nombres arbitrarios, el resultado es
   determinista (misma entrada → misma salida) y válido (Art. II.5).
