# Informe de implementación: Spec 007 — Scoring con Clasificador Lineal

**Rama**: `feature/scoring-genetico` · **Fecha**: 2026-10-28

## Resumen

Reemplazo exitoso del algoritmo genético (32 pesos hardcoded + sigmoide con sesgo) por un clasificador lineal pre-entrenado. Los coeficientes provienen de una regresión logística entrenada sobre `100correos.csv` y exportada como `data/modelo/clasificador_v1.json`. En runtime, `score_clasificador = 100 × σ(Σ wᵢ·geneᵢ + b)` — producto punto en Python puro, cero dependencias nuevas.

## Modelo entrenado

| Métrica | Valor |
|---|---|
| Accuracy | 0.94 |
| Recall | 0.9655 |
| F1 | 0.9492 |
| Score 0 genes | 24.52 (< 30, AC-SCO-01 PASS) |
| Intercepto | -1.124259 |
| Solver | lbfgs |
| C | 1.0 |

## Pruebas

```
437 passed, 1 skipped (gitleaks no instalado)
```

### Cobertura

| Módulo | Cobertura |
|---|---|
| scoring/__init__.py | 100% |
| scoring/configuracion.py | 100% |
| scoring/modelos.py | 95% |
| scoring/motor.py | 82% |
| **Total scoring + modelo + genetic_logic** | **89.12%** |

Supera el umbral constitucional de 80% (Art. II.3).

### Compuertas de calidad

```
[PASS] longitud_archivos
[PASS] nombre_rama
[PASS] cobertura
[PASS] trazabilidad_ac
[PASS] secretos
[FAIL] dependencias (no bloqueante — vulnerabilidades preexistentes, scope spec 014)
[PASS] lint
[PASS] tipos
```

## Trazabilidad AC → prueba

| AC | Descripción | Prueba | Estado |
|---|---|---|---|
| AC-SCO-01 | 0 genes → score < 30 | test_ac_sco_01_score_bajo.py | PASS |
| AC-SCO-02 | Monotonicidad | test_ac_sco_02_monotonicidad.py (hypothesis) | PASS |
| AC-SCO-03 | version_modelo desde JSON | test_ac_sco_03_version.py | PASS |
| AC-SCO-04 | Evaluación conjunto | Pendiente merge spec 015 (report-only) | — |
| AC-SCO-05 | Límites (tope 60/100) | test_ac_sco_05_limites.py | PASS |
| AC-SCO-06 | Palabra completa | test_ac_sco_06_palabra_completa.py | PASS |

## Archivos creados

| Archivo | Líneas | Rol |
|---|---|---|
| src/level3_logic/modelo.py | 147 | ClasificadorLineal, cargar_modelo, predecir_probabilidad |
| src/level3_logic/scoring/__init__.py | 20 | API pública |
| src/level3_logic/scoring/modelos.py | 68 | ScoreFinal, BanderaScoring, ScoringError |
| src/level3_logic/scoring/configuracion.py | 60 | ConfigScoring, desde_entorno |
| src/level3_logic/scoring/motor.py | 155 | calcular_score_final (fachada) |
| data/modelo/clasificador_v1.json | 42 | Modelo entrenado (coeficientes + metadata) |
| scripts/entrenar_clasificador.py | 145 | Entrenamiento offline (NO runtime) |

## Archivos modificados

| Archivo | Cambio |
|---|---|
| src/level3_logic/genetic_logic.py | ConfigGenetico, contiene_palabra_completa (FR-004), FR-005, scoring con modelo |
| src/level2_agent/agent.py | _genetic_score usa calcular_score_final, score_clasificador + version_modelo |
| src/level2_agent/models.py | PhishingReport gana score_clasificador, version_modelo |
| scripts/verify.py | +cov/lint paths para scoring/ y modelo.py |
| pyproject.toml | +mypy strict override para scoring + modelo |
| .env.example | +DOMINIOS_PROVEEDORES_CONFIANZA, +RUTA_MODELO |
| README.md | Árbol actualizado con scoring/ y modelo.py |
| AGENTS.md | Nota AG reemplazada por clasificador lineal |

## Desviaciones

1. **correo_c cambia de ruta**: con el clasificador, `correo_c` puntúa 76.44 (> 75) en vez de 30-75. Esto es correcto — el clasificador detecta mejor el phishing. Se actualizó la aserción en `test_ac_mem_02_independencia.py`.
2. **AC-SCO-04 pendiente**: requiere merge de la rama `test/conjunto-evaluacion` (spec 015). Report-only cuando esté disponible.
3. **`data/pesos/` no se borró**: no existía en esta rama; no hay archivos obsoletos que limpiar.

## Commits

```
b3185c0 feat(spec-007): T024-T027 polish — lint/mypy limpios, verify.py PASS
a6e8f3f feat(spec-007): T015-T021 implementacion completa
6fb3997 feat(spec-007): T004 entrenar_clasificador.py + clasificador_v1.json
xxxxxxx feat(spec-007): T006 modelo.py
xxxxxxx test(spec-007): T005 test_modelo.py
xxxxxxx test(spec-007): T007-T013 pruebas rojas
99f1177 feat(spec-007): T001-T003 setup
0e4743f docs(spec-007): tasks.md
167c572 docs(spec-007): re-plan para clasificador lineal
b0c0e2d docs(spec-007): reemplazar AG por clasificador lineal (spec rewrite)
```
