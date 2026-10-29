# Data Model: Scoring con Clasificador Lineal y Banderas (spec 007)

**Rama**: `feature/scoring-genetico` · Fuentes: spec actualizada, `genetic_logic.py`, APIs 003/004/005, contrato 012.

## ClasificadorLineal (Pydantic) — `src/level3_logic/modelo.py`

Contenido de `data/modelo/clasificador_v1.json`. Validado en la carga (Art. III.4).

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `version` | `str` | `min_length=1` (p. ej. `"clasificador_v1"`) | Archivo |
| `fecha` | `str` | ISO `YYYY-MM-DD` | Archivo |
| `conjunto_entrenamiento` | `str` | `min_length=1` | Archivo |
| `hiperparametros` | `Hiperparametros` | Pydantic nested (solver, C, max_iter, random_state) | Archivo |
| `metricas_entrenamiento` | `MetricasEntrenamiento` | Pydantic nested (accuracy, recall, f1) | Archivo |
| `intercepto` | `float` | sin cota | Archivo (del modelo sklearn) |
| `coeficientes` | `dict[str, float]` | **exactamente** las 32 claves de `MAPEO_INDICES` (validador `model_validator`) | Archivo (del modelo sklearn) |

**Funciones del módulo**:
- `cargar_modelo(ruta: Path | None = None) -> ClasificadorLineal` — default `data/modelo/clasificador_v1.json`; cache de proceso; JSON ilegible/schema inválido ⇒ `ModeloError`.
- `predecir_probabilidad(modelo: ClasificadorLineal, genes: Sequence[int]) -> float` — `σ(Σ wᵢ·geneᵢ + b)` en Python puro (0 deps).

## ScoreFinal (Pydantic) — `src/level3_logic/scoring/modelos.py`

| Campo | Tipo | Validación | Notas |
|---|---|---|---|
| `score_final` | `int` | `ge=0`, `le=100` | Entero (M09) |
| `score_clasificador` | `float` | `ge=0`, `le=100`, 2 decimales | Aporte del clasificador lineal |
| `puntos_banderas` | `int` | `ge=0`, `le=TOPE_PUNTOS_BANDERAS` (importado) | Suma 5.1+5.2+5.3 acotada |
| `version_modelo` | `str` | `min_length=1` | Del JSON (AC-SCO-03) |
| `genes_implicados` | `list[GenImplicado]` | default `[]` | `{"caracteristica": str, "peso": float}` |
| `banderas` | `list[BanderaScoring]` | default `[]` | Trazabilidad interna |

Validación: `score_final == min(100, round(score_clasificador + puntos_banderas))`.

## BanderaScoring, ConfigScoring, DependenciasScoring

Idénticos al plan anterior (D1/D5/D6): `origen: Literal["cabeceras","urls","adjuntos"]`, `codigo`, `puntos`; `ConfigScoring.desde_entorno()` con `DOMINIOS_PROPIOS`, `DOMINIOS_PROVEEDORES_CONFIANZA`, `RUTA_MODELO`; `DependenciasScoring` (cliente_rdap, deps_urls, ahora).

## Genes (índices fijos, sin cambio)

`MAPEO_INDICES` conserva los 32 nombres y orden. Comportamientos corregidos en `genetic_logic.py`:

| Índice | Gen | Cambio |
|---|---|---|
| 0 | `dominio_externo` | FR-005: condicionado a listas |
| 28 | `mismatch_dominio_url` | FR-005: idem |
| 5–9, 13–14, 17–18, 22–24, 30 | genes léxicos | FR-004: palabra completa |
| — | scoring | `score = 100 × σ(Σ coeficientes[gene] * gene + intercepto)` — coeficientes del modelo, no PESOS_AG |

## Relaciones

```text
data/modelo/clasificador_v1.json ──cargar_modelo()──▶ ClasificadorLineal ──evaluate()──▶ score_clasificador (+genes_implicados, version_modelo)
EmailData ──┬─ evaluate() (genetic_logic, corregido) ──────────────┐
            ├─ evaluar_banderas() (spec 003) → puntos_totales ─────┤
            ├─ analizar_urls() (spec 004) → Σ banderas[].puntos ───┼──▶ ScoreFinal ──▶ agent.py
            └─ adjuntos_analizados (spec 005, inyectados) ─────────┘
```
