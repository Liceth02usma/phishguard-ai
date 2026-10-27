# Implementation Plan: Scoring Genético con Banderas

**Branch**: `feature/scoring-genetico` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-scoring-genetico/spec.md`

## Summary

Crear un motor de puntuación pura y reproducible que conserve los 32 genes y la sigmoide como señal heurística, corrija los defectos del M10 (pesos negativos sin contrapeso, score 50 con 0 genes, coincidencias por subcadena, `dominio_externo`/`mismatch` sin listas de confianza), componga `score_final = min(100, score_genetico + puntos_banderas)` con tope de 60 (banderas nunca restan) y versione los pesos en `data/pesos/pesos_v1.json` guardando `version_pesos` en cada análisis. Se compone con las APIs ya entregadas por las specs 003 (`evaluar_banderas`), 004 (`analizar_urls`) y 005 (`analizar_adjunto`), y se cablea en `agent.py` para cumplir el contrato publicado de la spec 012 (`score`, `score_genetico`, `version_pesos`).

## Technical Context

**Language/Version**: Python 3.11.9 (requisito del proyecto: 3.10+)

**Primary Dependencies**: pydantic 2.14.1 (modelos), hypothesis (pruebas de propiedades), `requests` (vía puertos de 003/004). **Cero dependencias nuevas**.

**Storage**: archivo versionado `data/pesos/pesos_v1.json` (pesos + sesgo + metadata de entrenamiento). Sin base de datos.

**Testing**: pytest 8.2.2 + hypothesis sobre `tests/unit/`; dobles inyectados (reloj, DNS/HTTP, RDAP) — **sin red real** (Art. II.5).

**Target Platform**: Windows-primario, multiplataforma.

**Project Type**: módulo de librería dentro del pipeline (backend), cableado en `src/level2_agent/agent.py`.

**Performance Goals**: puntuación pura sin red (los puertos con red —RDAP, expansión de URLs— se inyectan; sus defaults son de producción).

**Constraints**: sin dependencias nuevas; `mypy --strict` en código nuevo; ≤ 500 líneas/archivo; sin red ni hora/azar sin controlar en pruebas; cadenas en español.

**Scale/Scope**: 32 genes, catálogos 5.1 (16 banderas) + 5.2 (13) + 5.3 (9), un archivo de pesos versionado. Solo la spec 007 (sin reglas duras ni veredicto: eso es la 008; sin VT: 006).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Estado | Evidencia / nota |
|---|---|---|
| 0 — Integridad | PASS | Los pesos del CSV/fixtures se tratan como dato; nada de esto ejecuta instrucciones de datos. Sin secretos en artefactos. |
| I — Rama | PASS | Rama `feature/scoring-genetico` creada antes de escribir documentos (cumple `^(feature\|fix\|refactor\|chore\|test\|docs)/[a-z0-9]+(-[a-z0-9]+)*$`). Sin commits en `main`. |
| II — Pruebas primero | PASS | TDD rojo→verde; técnicas: **análisis de valores límite** (obligatorio: tope 60 y `min(100,…)` en 59/60/61 y 99/100/101 = AC-SCO-05), **pruebas de propiedades** con `hypothesis` (monotonicidad, AC-SCO-02), **partición de equivalencia** (genes por grupos y listas de dominios), más **regresión** por la metadata de fixtures que cambia. Cada AC con `@pytest.mark.ac("AC-SCO-NN")`; ≥ 80 % líneas y ramas en código nuevo **y modificado** (`genetic_logic.py` entra a la compuerta de cobertura); deterministas (doubles, sin red). |
| III — Buenas prácticas | PASS | Archivos nuevos < 300 líneas; `genetic_logic.py` modificado queda < 450; funciones ≤ 40 líneas; anotaciones de tipo y `mypy --strict` vía override aditivo en `pyproject.toml`; modelos Pydantic; constantes con nombre (`TOPE_PUNTOS_BANDERAS` **importado** de `banderas.modelos`, no redefinido); patrones: **Facade** (`calcular_score_final` como fachada única), **Factory/Config** (`desde_entorno`), inyección de dependencias (reloj/RDAP/HTTP). `ruff` sobre los módulos nuevos. |
| IV — Definition of Done | PASS (planificado) | `scripts/verify.py` EXIT=0; trazabilidad AC completa; README/.env.example/contratos actualizados; informe final con desviaciones. |
| V — Seguridad y datos | PASS | Sin secretos; sin PII nueva (los pesos son numéricos); acciones externas: ninguna (scoring puro); red solo por puertos inyectables con defaults de producción (documentado: `test_pipeline.py` es runner de integración vivo, no corre en CI). |
| VI — Simplicidad y alcance | PASS | Solo FR-001..FR-007; sin reentrenamiento (solo revisión documental de pesos negativos, FR-007); sin umbrales nuevos inventados (30/60/100 vienen de la spec/M09/M10); valores desconocidos marcados `[VERIFICAR]`. |
| VII — Gobernanza | PASS | Verificación de cumplimiento en plan y tasks; ninguna enmienda a la constitución. |

**Complexity Tracking**: sin violaciones — tabla vacía.

## Project Structure

### Documentation (this feature)

```text
specs/007-scoring-genetico/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones D1–D10
├── data-model.md        # Fase 1: PesosGeneticos, ScoreFinal, BanderaScoring, ConfigScoring
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   └── calcular-score-final.md   # Contrato de la API pública del paquete scoring
└── tasks.md             # Fase 2 (/speckit.tasks — NO creado por este comando)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── agent.py                      # MODIFICADO: _genetic_score → calcular_score_final; reportes con score_genetico + version_pesos
│   ├── banderas/                     # SIN CAMBIOS (consumido: evaluar_banderas)
│   ├── analisis_urls/                # SIN CAMBIOS (consumido: analizar_urls)
│   └── adjuntos/                     # SIN CAMBIOS (consumido: analizar_adjunto por parámetro)
└── level3_logic/
    ├── pesos.py                      # NUEVO: schema + carga/validación de pesos_v1.json (con cache)
    ├── genetic_logic.py              # MODIFICADO: sesgo (FR-003), palabra completa (FR-004), listas (FR-005), version_pesos (FR-006)
    └── scoring/                      # NUEVO paquete
        ├── __init__.py               # API pública
        ├── configuracion.py          # ConfigScoring.desde_entorno (DOMINIOS_PROPIOS, DOMINIOS_PROVEEDORES_CONFIANZA)
        ├── modelos.py                # ScoreFinal, BanderaScoring, ScoringError
        └── motor.py                  # calcular_score_final (fachada de composición)

data/pesos/pesos_v1.json              # NUEVO: 32 pesos + sesgo + metadata (conjunto, semilla, fecha)

tests/unit/
├── test_ac_sco_01_score_bajo.py      # 0 genes < 30
├── test_ac_sco_02_monotonicidad.py   # propiedades hypothesis
├── test_ac_sco_03_version.py         # version_pesos en resultado y reporte
├── test_ac_sco_05_limites.py         # tabla 59/60/61 y 99/100/101
├── test_ac_sco_06_palabra_completa.py
├── test_pesos.py                     # loader: schema, cache, errores
├── test_genetico_genes.py            # matriz de genes (cobertura de genetic_logic modificado)
└── test_scoring_motor.py             # composición con dobles de 003/004/005

scripts/verify.py                     # MODIFICADO (aditivo): --cov y RUTAS para scoring/pesos/genetic_logic
pyproject.toml                        # MODIFICADO (aditivo): override mypy-strict para paquete scoring + pesos
.env.example                          # MODIFICADO (aditivo): DOMINIOS_PROVEEDORES_CONFIANZA
README.md / AGENTS.md                 # MODIFICADOS (aditivo): nota del módulo scoring y pesos versionados
```

**Structure Decision**: paquete nuevo `src/level3_logic/scoring/` junto al `genetic_logic.py` existente (misma raíz de nivel 3), reutilizando las APIs públicas de 003/004/005 sin tocarlas. `agent.py` cablea la fachada `calcular_score_final` reemplazando `_genetic_score`; los umbrales 30/75 de `models.py` quedan intactos (los reemplaza la spec 008).

## Post-Design Constitution Re-check (tras Fase 1)

| Requisito | Estado |
|---|---|
| Sin dependencias nuevas | PASS — solo pydantic/hypothesis ya presentes |
| Sin red en pruebas unitarias | PASS — el contrato define puertos inyectables (`cliente_rdap`, `deps_urls`) con dobles en `tests/unit` |
| Sin cambios fuera de alcance | PASS — `banderas/`, `analisis_urls/`, `adjuntos/`, `models.py` sin tocar; `agent.py` solo el cableado mínimo exigido por el contrato 012 |
| Cobertura ≥ 80 % en modificado | PASS (planificado) — `genetic_logic.py` entra a la compuerta con matriz de genes |
| Contratos/README/.env.example actualizados | PASS (planificado) — tareas T0xx dedicadas |
