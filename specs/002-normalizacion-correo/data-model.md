# Data Model: Normalización y Saneado de Correo (spec 002)

Entidades, constantes y reglas de validación. Todo vive en `src/level2_agent/models.py`
(entidades) y `src/level2_agent/normalizacion/` (comportamiento).

## Entidades

### `Cabecera` (NUEVA — Pydantic)

| Campo | Tipo | Reglas |
|---|---|---|
| `nombre` | `str` | Nombre de cabecera tal cual aparece (se normaliza a minúsculas solo al buscar; se conserva el original) |
| `valor` | `str` | Valor ya decodificado (`policy.default` resuelve RFC 2047) |

Se almacenan en orden físico del mensaje; las repetidas (`Received`) generan varias
instancias (AC-NORM-01). Prohibido diccionario (plan M02).

### `Adjunto` (NUEVO — Pydantic)

| Campo | Tipo | Reglas |
|---|---|---|
| `nombre` | `str` | Nombre de archivo; vacío → `"adjunto_sin_nombre"`; se procesa en memoria, nunca a disco (Art. V.5) |
| `tipo_declarado` | `str` | `Content-Type` declarado por la parte (no se infiere el real — M05 lo hará) |
| `tamano_bytes` | `int` | `len` del payload decodificado |
| `sha256` | `str` | Hex digest de `hashlib.sha256` sobre los bytes en memoria |

### `EmailData` (AMPLIADO — Pydantic, campo existente en `models.py`)

Se conservan los 6 campos legacy con sus tipos (D4): `htmlBody`, `headers` (JSON str),
`subject`, `recipient`, `textBody`, `message_id`. Nuevos campos, todos con default para no
romper constructores existentes:

| Campo | Tipo | Default | Reglas |
|---|---|---|---|
| `cabeceras` | `List[Cabecera]` | `[]` | Fuente única de verdad de cabeceras |
| `texto_limpio` | `str` | `""` | Salida de `html_a_texto` + parte `text/plain`, saneada y truncada a `LIMITE_CARACTERES_TEXTO` |
| `urls` | `List[str]` | `[]` | Extraídas de href/src/action/texto; deduplicadas; ≤ `LIMITE_URLS` |
| `adjuntos` | `List[Adjunto]` | `[]` | ≤ `LIMITE_ADJUNTOS`; SHA-256 calculado |
| `origen` | `Literal["gmail", "api"]` | `"gmail"` | `.eml` se recibe por la ruta API → `origen="api"` |
| `banderas` | `List[str]` | `[]` | `LIMITE_EXCEDIDO` y/o `ENTRADA_DEGRADADA` (constantes, ver abajo) |
| `revision_manual` | `bool` | `False` | `True` si hay cualquier bandera (Art. V.1) |

Además: `htmlBody` pasa a `Field(..., exclude=True)` — FR-001 "solo en memoria, nunca
persistido"; `model_dump()`/`model_dump_json()` ya no lo incluyen. `repr=False` evita que
aparezca en logs.

**Reglas de transición**: el normalizador puebla legacy + nuevos campos de forma coherente
(`headers` se deriva de `cabeceras`; `textBody` ≈ texto original sin saneado, `texto_limpio`
= la versión saneada). Specs 003–05 migran y retiran el legacy.

## Constantes (módulo `limites.py` / `enmascarado.py`)

| Constante | Valor | Origen |
|---|---|---|
| `LIMITE_BYTES_CORREO` | `25 * 1024 * 1024` (26 214 400) | FR-004 (decisión D6: MB binario) |
| `LIMITE_CARACTERES_TEXTO` | `20_000` | FR-004 |
| `LIMITE_URLS` | `200` | FR-004 |
| `LIMITE_ADJUNTOS` | `20` | FR-004 |
| `LIMITE_NIVELES_MIME` | `10` | FR-004 |
| `BANDERA_LIMITE_EXCEDIDO` | `"LIMITE_EXCEDIDO"` | FR-004 (nombre exigido por spec) |
| `BANDERA_ENTRADA_DEGRADADA` | `"ENTRADA_DEGRADADA"` | AC-NORM-06 (nombre de diseño, D9) |
| `TEXTO_OCULTO_MARCADOR` | `"[NÚMERO_OCULTO]"` | FR-005 |

## Estructura interna (no persistida): `CorreoBruto`

Dataclass intermedia de `parseo_mime.py` — salida del Adapter y entrada del pipeline:
`cabeceras: List[Cabecera]`, `cuerpo_html: str`, `cuerpo_texto: str`,
`partes_adjunto: List[bytes + metadatos]`, `profundidad_max_mime: int`,
`bytes_totales: int`, `problemas: List[str]` (codificaciones que fallaron → degradada).

## Máquina de estados de banderas (simplificada)

```text
entrada → parsear → ¿ok? ──no──→ [ENTRADA_DEGRADADA] ─┐
                │                                     ├──→ revision_manual = True
                └── sí → evaluar 5 límites ──excede──→ [LIMITE_EXCEDIDO] ─┘
                                  │
                                  └── dentro → banderas = [] y revision_manual = False
```

Cualquier bandera ⇒ `revision_manual=True` (V.1). Un correo puede acumular varias
`LIMITE_EXCEDIDO`… se registra la constante UNA vez (la bandera es binaria por tipo) — la
lista `banderas` no duplica entradas idénticas.

## Reglas de validación Pydantic

- `urls`: items no vacíos (URL vacía se descarta al extraer, no en validación).
- `sha256`: 64 caracteres hexadecimales.
- `tamano_bytes` ≥ 0.
- `origen`: solo `"gmail"` | `"api"`.
- Sin campos obligatorios nuevos (compatibilidad D4).
