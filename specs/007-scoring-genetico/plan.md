# Implementation Plan: Scoring con Clasificador Lineal y Banderas

**Branch**: `feature/scoring-genetico` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-scoring-genetico/spec.md`

## Summary

Reemplazar el algoritmo genético (32 pesos hardcoded + sigmoide con sesgo) por un clasificador lineal pre-entrenado: los coeficientes `w` y el intercepto `b` provienen de una regresión logística entrenada formalmente sobre `100correos.csv` y exportada como `data/modelo/clasificador_v1.json`. En runtime, `score_clasificador = 100 × σ(Σ wᵢ·geneᵢ + b)` — producto punto en Python puro, cero dependencias nuevas. Componer con banderas (003/004/005): `score_final = min(100, score_clasificador + puntos_banderas)` con tope 60. Versionar el modelo y guardar `version_modelo` en cada análisis. Cablear en `agent.py` para cumplir el contrato 012 (`score`, `score_clasificador`, `version_modelo`).

## Technical Context

**Language/Version**: Python 3.11.9 (requisito del proyecto: 3.10+)

**Primary Dependencies**: pydantic 2.14.1 (modelos), hypothesis (pruebas de propiedades), `requests` (vía puertos de 003/004). **Cero dependencias nuevas en runtime**. scikit-learn solo para el script de entrenamiento offline.

**Storage**: archivo versionado `data/modelo/clasificador_v1.json` (coeficientes + intercepto + metadata). Sin base de datos.

**Testing**: pytest 8.2.2 + hypothesis sobre `tests/unit/`; dobles inyectados — **sin red real** (Art. II.5).

**Target Platform**: Windows-primario, multiplataforma.

**Project Type**: módulo de librería dentro del pipeline (backend), cableado en `src/level2_agent/agent.py`.

**Performance Goals**: puntuación pura sin red (los puertos con red se inyectan; defaults de producción).

**Constraints**: sin dependencias runtime nuevas; `mypy --strict` en código nuevo; ≤ 500 líneas/archivo; sin red ni hora/azar sin controlar en pruebas; cadenas en español.

**Scale/Scope**: 32 características (genes), catálogos 5.1 (16) + 5.2 (13) + 5.3 (9), un archivo de modelo versionado. Solo la spec 007.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Estado | Evidencia / nota |
|---|---|---|
| 0 — Integridad | PASS | Los coeficientes del modelo se tratan como dato; el CSV de entrenamiento es dato. Sin secretos. |
| I — Rama | PASS | Rama `feature/scoring-genetico` creada antes de escribir documentos. Sin commits en `main`. |
| II — Pruebas primero | PASS | TDD rojo→verde; técnicas: **análisis de valores límite** (tope 60 y `min(100,…)` = AC-SCO-05), **pruebas de propiedades** con `hypothesis` (monotonicidad, AC-SCO-02), **partición de equivalencia** (genes por grupos y listas de dominios), más **regresión** por la metadata de fixtures que cambia. Cada AC con `@pytest.mark.ac("AC-SCO-NN")`; ≥ 80 % líneas y ramas en código nuevo y modificado; deterministas (doubles). |
| III — Buenas prácticas | PASS | Archivos nuevos < 300 líneas; `genetic_logic.py` modificado < 450; funciones ≤ 40 líneas; anotaciones de tipo y `mypy --strict` vía override aditivo; modelos Pydantic; constantes con nombre (`TOPE_PUNTOS_BANDERAS` importado de `banderas.modelos`); patrones: **Facade** (`calcular_score_final`), **Factory** (`desde_entorno`), inyección de dependencias. `ruff` sobre módulos nuevos. |
| IV — Definition of Done | PASS (planificado) | `scripts/verify.py` EXIT=0; trazabilidad AC completa; README/.env.example/contratos actualizados; informe final. |
| V — Seguridad y datos | PASS | Sin secretos; sin PII nueva; red solo por puertos inyectables con defaults de producción. |
| VI — Simplicidad y alcance | PASS | Solo FR-001..FR-007; sin reentrenamiento automático; sin umbrales nuevos inventados; valores desconocidos marcados `[VERIFICAR]`. |
| VII — Gobernanza | PASS | Verificación de cumplimiento en plan y tasks; ninguna enmienda a la constitución. |

**Complexity Tracking**: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/007-scoring-genetico/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones D1–D13
├── data-model.md        # Fase 1: ClasificadorLineal, ScoreFinal, BanderaScoring, ConfigScoring
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   └── calcular-score-final.md   # Contrato de la API pública
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── agent.py                      # MODIFICADO: score_clasificador + version_modelo en reporte
│   ├── banderas/                     # SIN CAMBIOS (consumido)
│   ├── analisis_urls/                # SIN CAMBIOS (consumido)
│   └── adjuntos/                     # SIN CAMBIOS (consumido por parámetro)
└── level3_logic/
    ├── modelo.py                     # NUEVO: schema + carga/validación de clasificador_v1.json
    ├── genetic_logic.py              # MODIFICADO: scoring con coeficientes del modelo, palabra completa, listas
    └── scoring/                      # NUEVO paquete
        ├── __init__.py               # API pública
        ├── configuracion.py          # ConfigScoring.desde_entorno
        ├── modelos.py                # ScoreFinal, BanderaScoring, ScoringError
        └── motor.py                  # calcular_score_final (fachada)

data/modelo/clasificador_v1.json     # NUEVO: 32 coeficientes + intercepto + metadata
scripts/entrenar_clasificador.py     # NUEVO: entrenamiento offline (NO runtime)

tests/unit/
├── test_ac_sco_01_score_bajo.py
├── test_ac_sco_02_monotonicidad.py
├── test_ac_sco_03_version.py
├── test_ac_sco_05_limites.py
├── test_ac_sco_06_palabra_completa.py
├── test_modelo.py                   # loader: schema, cache, errores
├── test_genetico_genes.py           # matriz de genes (cobertura genetic_logic)
└── test_scoring_motor.py            # composición con dobles 003/004/005

scripts/verify.py                     # MODIFICADO (aditivo): --cov y RUTAS
pyproject.toml                        # MODIFICADO (aditivo): override mypy-strict
.env.example                          # MODIFICADO (aditivo): DOMINIOS_PROVEEDORES_CONFIANZA
README.md / AGENTS.md                 # MODIFICADOS (aditivo)
```

**Structure Decision**: paquete `src/level3_logic/scoring/` + módulo `src/level3_logic/modelo.py` (fuera del paquete para evitar ciclos: `genetic_logic` importa `modelo`; `scoring.motor` importa `genetic_logic`). El script de entrenamiento es herramienta offline, no parte del runtime.

## Post-Design Constitution Re-check

| Requisito | Estado |
|---|---|
| Sin dependencias runtime nuevas | PASS — scikit-learn solo en el script de entrenamiento |
| Sin red en pruebas unitarias | PASS — puertos inyectables con dobles |
| Sin cambios fuera de alcance | PASS — `banderas/`, `analisis_urls/`, `adjuntos/`, `models.py` sin tocar |
| Cobertura ≥ 80 % en modificado | PASS (planificado) — `genetic_logic.py` entra a la compuerta |
| Contratos/README/.env.example actualizados | PASS (planificado) |
