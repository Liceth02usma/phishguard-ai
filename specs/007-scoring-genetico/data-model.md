# Data Model: Scoring Genético con Banderas (spec 007)

**Rama**: `feature/scoring-genetico` · Fuentes: `src/level3_logic/genetic_logic.py`, modelos de 003/004/005, contrato 012.

## PesosGeneticos (Pydantic) — `src/level3_logic/pesos.py`

Representa el contenido de `data/pesos/pesos_v1.json`. Se valida en la carga (Art. III.4).

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `version` | `str` | `min_length=1`; identifica la versión (p. ej. `"pesos_v1"`). Es la fuente de `version_pesos` (FR-006) | Archivo |
| `fecha` | `str` | ISO `YYYY-MM-DD` vía `pattern` | Archivo |
| `conjunto_entrenamiento` | `str` | `min_length=1` (FR-007: documentar el conjunto) | Archivo |
| `semilla` | `int` | `ge=0` (FR-007: documentar la semilla) | Archivo |
| `sesgo` | `float` | sin cota; default factible `−1.0` (research D2; `[VERIFICAR]` calibración M13) | Archivo |
| `pesos` | `dict[str, float]` | **exactamente** las 32 claves de `MAPEO_INDICES` (validador `model_validator`: faltantes y sobrantes ⇒ `PesosError`) | Archivo (v1 = los valores actuales de `PESOS_AG`) |

**Funciones del módulo**:
- `cargar_pesos(ruta: Path | None = None) -> PesosGeneticos` — default `data/pesos/pesos_v1.json` (relativo a la raíz del proyecto); cache de proceso (segunda llamada no relee disco); JSON ilegible / schema inválido ⇒ `PesosError` (subclase de `ScoringError`) con mensaje útil (Art. III.9).
- `VERSION_PESOS` deja de ser constante hardcodeada en `genetic_logic.py`: se deriva de `pesos.version`.

**Archivo `data/pesos/pesos_v1.json` (ejemplo de forma)**:

```json
{
  "version": "pesos_v1",
  "fecha": "2026-10-27",
  "conjunto_entrenamiento": "100correos.csv (corpus CEAS_08, vectores de 32 genes + label, aportado por el usuario)",
  "semilla": 42,
  "sesgo": -1.0,
  "nota": "Pesos v1 = PESOS_AG historic. Revisión de pesos negativos contra el conjunto etiquetado: FR-007/spec 007 (report-only, sin reentrenar). Fecha/semilla originales del entrenamiento GA: [VERIFICAR].",
  "pesos": { "cuerpo_corto": 0.935, "...": "32 claves exactas de MAPEO_INDICES", "apelacion_miedo": -0.871 }
}
```

## ScoreFinal (Pydantic) — `src/level3_logic/scoring/modelos.py`

Salida de `calcular_score_final`. Invariante central (FR-002): `score_final == min(100, redondeado(score_genetico + puntos_banderas))`.

| Campo | Tipo | Validación | Notas |
|---|---|---|---|
| `score_final` | `int` | `ge=0`, `le=100` | Entero (M09: "score_final, entero 0 a 100") |
| `score_genetico` | `float` | `ge=0`, `le=100`, 2 decimales | Aporte del AG con sesgo (FR-001/FR-003); va al contrato 012 como `score_genetico` |
| `puntos_banderas` | `int` | `ge=0`, `le=TOPE_PUNTOS_BANDERAS` (constante **importada** de `banderas/modelos.py`) | Suma de catálogos 5.1+5.2+5.3 acotada (D1); nunca negativos ⇒ nunca resta |
| `version_pesos` | `str` | `min_length=1` | Copiado de `PesosGeneticos.version` (AC-SCO-03) |
| `genes_implicados` | `list[GenImplicado]` | default `[]` | `{"caracteristica": str, "peso": float}` (compatibilidad con el shape actual de `evaluate`) |
| `banderas` | `list[BanderaScoring]` | default `[]` | Trazabilidad agregada (interna; **no** forma parte del contrato 012) |

Validación por `model_validator`: recalcular `min(100, round(score_genetico + puntos_banderas))` y exigir igualdad con `score_final` (protege contra errores de composición).

## BanderaScoring (Pydantic) — `scoring/modelos.py`

| Campo | Tipo | Validación |
|---|---|---|
| `origen` | `Literal["cabeceras", "urls", "adjuntos"]` | — |
| `codigo` | `str` | `min_length=1` (códigos de los catálogos 5.1/5.2/5.3) |
| `puntos` | `int` | `ge=0` |

## ConfigScoring — `scoring/configuracion.py`

| Campo | Tipo | Env (coma-separada) | Default |
|---|---|---|---|
| `dominios_propios` | `tuple[str, ...]` | `DOMINIOS_PROPIOS` (reutiliza la env de la spec 003) | `()` |
| `proveedores_confianza` | `tuple[str, ...]` | `DOMINIOS_PROVEEDORES_CONFIANZA` (nueva) | constante `PROVEEDORES_CONFIANZA_POR_DEFECTO` (research D5) |
| `ruta_pesos` | `Path \| None` | `RUTA_PESOS` (opcional) | `None` ⇒ `data/pesos/pesos_v1.json` |

`ConfigScoring.desde_entorno()` lee `os.environ`; valores invalidados ⇒ `ScoringError`. Dominios normalizados a minúsculas y sin punto inicial.

## Dependencias inyectables — `scoring/motor.py`

`DependenciasScoring` (dataclass frozen, defaults de producción):
- `cliente_rdap: ClienteRDAP | None` → `None` ⇒ lo que use `evaluar_banderas` (`RequestsRDAP`, producción).
- `deps_urls: DependenciasURLs | None` → `None` ⇒ `dependencias_por_defecto()` de 004.
- `ahora: datetime | None` → `None` ⇒ reloj del sistema (producción); las pruebas inyectan reloj falso.

## Genes (índices fijos, sin cambio)

`MAPEO_INDICES` conserva los 32 nombres y su orden (FR-001). Comportamientos corregidos en `genetic_logic.py`:

| Índice | Gen | Cambio spec 007 |
|---|---|---|
| 0 | `dominio_externo` | FR-005: se activa solo si remitente ≠ destinatario **y** ninguno en (propios ∪ confianza) |
| 28 | `mismatch_dominio_url` | FR-005: idem con el dominio de la URL |
| 5–9, 13–14, 17–18, 22–24, 30 | genes léxicos | FR-004: coincidencia por palabra completa (`(?<!\w)…(?!\w)`, `IGNORECASE`) |
| — | sigmoide | FR-003: `100/(1+e^{-(Σ+b)})` con `b` = `pesos.sesgo`; 0 genes ⇒ 26.89 < 30 |

## Estados y transiciones

No aplica: el scoring es una **función pura** (mismo correo + mismos pesos + mismos insumos ⇒ mismo `ScoreFinal`, Art. II.5). La única mutación de proceso es la cache de `pesos_v1.json` (idempotente).

## Relaciones

```text
data/pesos/pesos_v1.json ──cargar_pesos()──▶ PesosGeneticos ──evaluate()──▶ score_genetico (+genes_implicados, version_pesos)
EmailData ──┬─ evaluate() (genetic_logic, corregido) ────────────┐
            ├─ evaluar_banderas() (spec 003) → puntos_totales ───┤
            ├─ analizar_urls() (spec 004) → Σ banderas[].puntos ─┼──▶ ScoreFinal ──▶ agent.py: score=ruta 30/75 + report(score_genetico, version_pesos)
            └─ adjuntos_analizados (spec 005, inyectados) ───────┘
```
