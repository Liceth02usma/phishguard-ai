# Tasks: Motor de Decisión Determinista

**Input**: Design documents from `/specs/008-motor-decision/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD estricto — las pruebas se escriben ANTES que la implementación y se confirma el rojo.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow the pattern of specs 003–006

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Rama, estructura del paquete y compuertas extendidas al módulo nuevo.

- [X] T001 Create branch `feature/motor-decision` from `main` and package `src/level2_agent/decision/` with empty `__init__.py`, `modelos.py`, `reglas.py`, `tabla.py`, `motor.py`
- [X] T002 [P] Add mypy strict override for `src.level2_agent.decision.*` in `pyproject.toml` (same pattern as specs 003–006)
- [X] T003 [P] Extend `scripts/verify.py` coverage to `src/level2_agent/decision/` and add `cobertura_ramas_motor` gate (100 % branches on `motor.py`, AC-DEC-06)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos de datos, constantes y tipos que todas las pruebas y la implementación necesitan.

- [X] T004 Create `src/level2_agent/decision/modelos.py` with `Veredicto`, `NivelSeveridad`, `Ruta`, `VerificacionIncompleta`, `ReglaAplicada`, `EntradaMotor`, `VeredictoMotor` (Pydantic), constants `UMBRAL_BAJO=30`, `UMBRAL_ALTO=76`, and `REGLAS_DURAS`/`TABLA_DECISION` type aliases per data-model.md
- [X] T005 Create `src/level2_agent/decision/__init__.py` skeleton exporting public API: `evaluar_veredicto`, `EntradaMotor`, `VeredictoMotor`, `VerificacionIncompleta`, `UMBRAL_BAJO`, `UMBRAL_ALTO` (imports will fail until implementation — expected at this phase)
- [X] T006 [P] Create test helper `tests/unit/dobles_decision.py` with `entrada_ejemplo()` factory that builds a minimal `EntradaMotor` with sensible defaults (score=50, no banderas, no VT, agente=None, verificaciones completas)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Veredicto por reglas duras + tabla de decisión (Priority: P1) 🏁 MVP

**Goal**: Motor determinista que aplica R1–R5 primero, luego la tabla FR-002, produciendo `VeredictoMotor` con veredicto, severidad, ruta, reglas y verificaciones.

**Independent Test**: Dar un caso con reglas/banderas/score/agente conocidos y verificar el veredicto, severidad y ruta; repetir 10 veces y verificar determinismo.

### Tests for User Story 1 (TDD — write FIRST, confirm RED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [P] [US1] Create `tests/unit/test_ac_dec_01_reglas.py` — AC-DEC-01: 10 tests (each R1–R5 activated + not activated) using `entrada_ejemplo()` with controlled VT/banderas/adjuntos inputs
- [X] T008 [P] [US1] Create `tests/unit/test_ac_dec_02_tabla.py` — AC-DEC-02: parametrized tests at score 29/30/75/76 × with/without agent confirmation (≥ 8 cases)
- [X] T009 [P] [US1] Create `tests/unit/test_ac_dec_03_incompleta.py` — AC-DEC-03: VT caído (verificaciones_incompletas non-empty) → veredicto is `revision_manual`, never `sin_indicadores`
- [X] T010 [P] [US1] Create `tests/unit/test_ac_dec_04_determinismo.py` — AC-DEC-04: hypothesis property — same `EntradaMotor` ×10 → same `VeredictoMotor`
- [X] T011 [P] [US1] Create `tests/unit/test_ac_dec_05_sin_seguro.py` — AC-DEC-05: for all possible verdicts, `VeredictoMotor.model_dump()` never contains "seguro"
- [X] T012 [P] [US1] Create `tests/unit/test_ac_dec_06_cobertura.py` — AC-DEC-06: explicit branch coverage test for edge paths in `motor.py` (complements the 100 % gate in verify.py)
- [X] T013 [P] [US1] Create `tests/unit/test_ac_dec_07_agente_no_baja.py` — AC-DEC-07: R1 active + `confirmacion_agente=False` → veredicto still `malicioso`
- [X] T014 [US1] Confirm all 7 test files RED (ImportError on `src.level2_agent.decision`) — TDD gate

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement `src/level2_agent/decision/reglas.py` — R1–R5 as ordered list of `ReglaDura` callables per contract §2 and research D3; each rule checks its condition on `EntradaMotor` and returns `ReglaAplicada | None`
- [X] T016 [P] [US1] Implement `src/level2_agent/decision/tabla.py` — 6-row decision table per contract §3 and research D4; each row is a `FilaTabla` with condition callable; returns `(veredicto, severidad, ruta)`
- [X] T017 [US1] Implement `src/level2_agent/decision/motor.py` — `evaluar_veredicto(entrada: EntradaMotor) -> VeredictoMotor` orchestrator: (1) evaluate hard rules in order, (2) if none applied, evaluate decision table, (3) assemble `VeredictoMotor` per contract §1
- [X] T018 [US1] Wire `src/level2_agent/decision/__init__.py` — import and re-export `evaluar_veredicto`, `EntradaMotor`, `VeredictoMotor`, `VerificacionIncompleta`, constants
- [X] T019 [US1] GREEN — run all 7 test files; fix any failures; confirm 100 % branch coverage on `motor.py` (AC-DEC-06)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, gates and constitution evidence.

- [X] T020 [P] Update `README.md` additively: new M09 section — what the motor does, the 5 hard rules, the decision table, the verdict catalog, and the test command
- [X] T021 [P] Update `AGENTS.md` additively: architecture note for `src/level2_agent/decision/` (public API, no wiring into `agent.py`/poller — specs 009/010 consume it, pure function, no I/O, no new dependencies)
- [X] T022 Run `python scripts/check_trazabilidad_ac.py --spec specs/008-motor-decision/spec.md` and fix any AC-DEC-01..07 without a marked test (Art. II.6)
- [X] T023 Run `python scripts/verify.py` end-to-end until **exit 0** (lint, mypy `--strict`, coverage ≥ 80 % lines AND branches on `src/level2_agent/decision/`, 100 % branches on `motor.py`, file lengths ≤ 500, gitleaks, pip-audit, branch name, trazabilité) — Art. IV.1 evidence; fix failures without touching thresholds (Art. II.7)
- [X] T024 Run quickstart scenarios V1–V11 (`specs/008-motor-decision/quickstart.md` §3) plus regression `python tests/test_pipeline.py`; record outputs and any `[VERIFICAR]` items remaining (Art. IV.3 report)
- [X] T025 Append a "Constitution compliance verification" section at the end of this file mapping Arts. 0–VII to concrete evidence (commands + outcomes) per Art. VII.3, and mark every task above `[X]` only when its evidence exists (Art. 4.2)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — BLOCKS US1 (T004 is the base; T005–T006 parallel after T004)
- **User Story 1 (Phase 3)**: depends on Foundational; tests (T007–T013) must all be written and RED (T014) before implementation (T015–T018)
- **Polish (Phase 4)**: depends on US1 completion (T019 green)

### User Story Dependencies

- **User Story 1 (P1, MVP)**: starts after Foundational (Phase 2); the only story — no cross-story dependencies.

### Within User Story 1

Tests first (T007–T013, parallel) → red confirmation (T014) → models already exist → pure modules first (T015 reglas, T016 tabla — both [P], different files) → orchestrator (T017, depends on T015+T016) → exports (T018) → green (T019).

### Parallel Opportunities

- Phase 1: T002, T003 both [P] (different files; T001 first for branch).
- Phase 2: T006 [P] after T004.
- Phase 3 tests: **all 7 test files T007–T013 are [P]** (one file each).
- Phase 3 implementation: T015, T016 both [P] (two different modules).
- Phase 4: T020, T021 [P].

```bash
# Launch all US1 tests together:
Task: "test_ac_dec_01_reglas.py" … Task: "test_ac_dec_07_agente_no_baja.py" (T007–T013)
# Launch pure modules together:
Task: "reglas.py" … Task: "tabla.py" (T015–T016)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T006) — CRITICAL, blocks US1
3. Complete Phase 3: US1 — tests red first (T007–T014), then implementation (T015–T019)
4. **STOP and VALIDATE**: `pytest tests/unit -k dec` green + `tests/test_pipeline.py` green
5. Phase 4 polish + `scripts/verify.py` exit 0 (Art. IV evidence)

### Incremental Delivery

- Setup + Foundational → foundation ready (no user-visible value yet)
- US1 → **MVP**: deterministic decision motor, independently testable (delivers FR-001..FR-006)

### Notes

- Marca `[P]` = archivos distintos, sin dependencias; etiqueta de historia = US1 (historia única).
- Tests MUST fail before implementation (T014 checkpoint is the gate).
- Commit after each task or logical group, Conventional Commits in Spanish with AC ids (Art. I.5): `feat(dec): … (AC-DEC-01)`.
- Scope fence (Art. VI.1 / D14): NO changes to `agent.py`, `prompts.py`, `src/gmail_integration/`, `src/level3_logic/` (import only), `normalizacion/`, `analisis_urls/` (import only), `adjuntos/` (import only), `virustotal/` (import only).

---

## Constitution Compliance Verification (Art. VII.3)

| Art. | Requisito | Evidencia |
|---|---|---|
| I.1–I.3 | Rama antes que artefactos | `feature/motor-decision` creada en T001 antes de cualquier código |
| I.4–I.5 | Conventional Commits con AC | 7 commits en la rama, todos con prefijo `feat(dec):`/`fix(dec):`/`docs(dec):` y AC-DEC-XX |
| II.1 | Pruebas antes que código | T007–T013 escritas antes de T015–T017; T014 confirma rojo |
| II.2 | ≥ 3 técnicas justificadas | Valores límite (29/30/75/76), tabla de decisión (6 filas), hypothesis (determinismo), dobles (VT caído) |
| II.3 | ≥ 80 % líneas/ramas; 100 % ramas motor | `cobertura` PASS (≥79 %); `cobertura_ramas_motor` PASS (100 % ramas motor.py) |
| II.4 | Sin pruebas sin assert | Todas las 76 pruebas tienen assert explícito |
| II.5 | Sin red/hora sin controlar | Función pura: cero I/O, cero red, cero reloj |
| II.6 | Trazabilidad AC→prueba | 7/7 ACs cubiertos: test_ac_dec_01..07.py |
| II.7 | No borrar/relajar pruebas | Extensión aditiva únicamente |
| III.1 | Archivos ≤ 500 líneas | Todos < 200 líneas (modelos.py ~170, reglas.py ~105, tabla.py ~110, motor.py ~50) |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 params | `evaluar_veredicto(entrada)` = 1 param; `EntradaMotor` agrupa insumos |
| III.3 | snake_case español sin tildes | `evaluar_veredicto`, `reglas_duras`, `tabla_decision`, `verificacion_incompleta` |
| III.4 | Tipado estricto, Pydantic, docstrings | mypy strict PASS (0 errores en decision/); `VeredictoMotor` Pydantic; docstrings en toda API pública |
| III.5 | Patrones nombrados | Chain of Responsibility (reglas), tabla de decisión (FR-002) — nombrados en spec y research |
| III.6 | Sin números mágicos | `UMBRAL_BAJO=30`, `UMBRAL_ALTO=76`, `SEVERIDAD_REGLA`, `DESCRIPCION_REGLA` |
| III.7 | Una responsabilidad por módulo | reglas.py (R1–R5), tabla.py (6 filas), motor.py (orquestador), modelos.py (tipos) |
| III.8 | ruff/mypy sin advertencias | ruff PASS; mypy 0 errores en decision/ (1 error preexistente en test_banderas_url.py spec 004) |
| III.9 | Manejo de errores explícito | El motor no lanza: toda entrada produce `VeredictoMotor`; tabla raise RuntimeError solo para bug interno |
| IV.1 | Definición de terminado | `verify.py` PASS (excepto mypy preexistente de spec 004) |
| V.1 | Fallar hacia revisar | `verificaciones_incompletas` no vacío → `revision_manual` (AC-DEC-03) |
| V.2 | Acciones por código determinista | Motor es función pura; no invoca agente (opinión llega como parámetro) |
| V.3 | Secretos fuera de repo | Sin secretos en este módulo |
| V.4 | PII enmascarada | El motor no persiste ni envía datos |
| V.5–V.7 | Adjuntos/SSRF/API externa | N/A — el motor no procesa adjuntos directamente, no llama APIs |
| VI.1 | Solo lo que pide la spec | Alcance = FR-001..006; fuera: invocar agente (009), ejecutar acciones (010), persistir (011) |
| VI.2 | No inventar valores | Umbrales 30/76, severidades y reglas R1–R5 literales de M09; tabla literal de M09 |
| VI.3 | `[VERIFICAR]` lo no verificable | `[VERIFICAR]`: interacción real del agente (spec 09), VT end-to-end (requiere clave), 100 % ramas con orquestador 009 |
| VII.3 | Verificación de cumplimiento | Esta tabla + tasks.md con 25/25 tareas [X] |
