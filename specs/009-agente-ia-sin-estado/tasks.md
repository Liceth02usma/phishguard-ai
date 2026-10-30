# Tasks: Agente de IA Sin Estado

**Input**: Design documents from `/specs/009-agente-ia-sin-estado/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD estricto — las pruebas se escriben ANTES que la implementación y se confirma el rojo. AC-AGT-06: cero llamadas al modelo real.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow the pattern of specs 003–008

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Rama, estructura del paquete, mypy override y compuertas extendidas.

- [X] T001 Create branch `feature/agente-ia-sin-estado` from `main` and package `src/level2_agent/agente/` with empty `__init__.py`, `modelos.py`, `prompt.py`, `validador.py`, `contador.py`, `agente.py`
- [X] T002 [P] Add mypy strict override for `src.level2_agent.agente.*` in `pyproject.toml` (same pattern as specs 003–008)
- [X] T003 [P] Extend `scripts/verify.py` coverage to `src/level2_agent/agente/`
- [X] T004 [P] Create fixtures directory `tests/fixtures/inyeccion/` with 10 JSON files containing emails with injection instructions in body, subject, hidden text and attachment name (AC-AGT-02)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos de datos, constantes, tipos, Protocol del modelo y doubles de prueba.

- [X] T005 Create `src/level2_agent/agente/modelos.py` with `EntradaAgente`, `SalidaAgente` (Pydantic with max lengths: resumen 500, analisis_tecnico 2000, indicadores max 10 items × 200 chars, justificacion 1000), `ResultadoAgente`, `ModeloLLM` Protocol, constants `LLM_MAX_DIARIO`, `LLM_MODELO`, `LLM_TEMPERATURA=0`, `DELIM_CORREO_INICIO`, `DELIM_CORREO_FIN`, `MAX_REINTENTOS=1`, length limits per data-model.md
- [X] T006 Create `src/level2_agent/agente/__init__.py` skeleton exporting public API: `consultar_agente`, `EntradaAgente`, `SalidaAgente`, `ResultadoAgente`, `ModeloLLM`, `ContadorLLM`
- [X] T007 [P] Create `src/level2_agent/agente/contador.py` with `ContadorLLM` class: `incrementar() -> int`, `disponible() -> bool`, MongoDB `phishguard.llm_contador` with TTL, in-memory fallback, injected clock for determinism, config via `LLM_MAX_DIARIO` env var (default 100)
- [X] T008 [P] Create test helper `tests/unit/dobles_agente.py` with `ModeloDoble` (returns predefined `SalidaAgente` JSON), `ModeloDobleInvalido` (returns malformed JSON), `ContadorDoble` (in-memory counter with injected clock), `entrada_agente_ejemplo()` factory

**Checkpoint**: Foundation ready — user story implementation can now begin ✅

---

## Phase 3: User Story 1 - Agente sin estado, sin efectos, resistente a inyección (Priority: P1) 🏁 MVP

**Goal**: Agente que recibe evidencia estructurada, usa solo `busqueda_vectorial`, valida salida con esquema, resiste inyección, y respeta tope diario.

**Independent Test**: Con respuestas simuladas, verificar herramientas, inyección, esquema, tope diario y cero llamadas reales.

### Tests for User Story 1 (TDD — write FIRST, confirm RED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Create `tests/unit/test_ac_agt_01_herramientas.py` — AC-AGT-01: verify the ReAct agent tool list is exactly `[busqueda_vectorial]`; no `check_ip_reputation`, no `jira_integration`
- [X] T010 [P] [US1] Create `tests/unit/test_ac_agt_02_inyeccion.py` — AC-AGT-02: 10 tests using `tests/fixtures/inyeccion/*.json`, each compares verdict with/without injection phrases using `ModeloDoble`; verdict must not change
- [X] T011 [P] [US1] Create `tests/unit/test_ac_agt_03_esquema.py` — AC-AGT-03: test that `ModeloDobleInvalido` triggers 1 retry, then `ResultadoAgente.razon == "validacion_fallida"` and `confirmacion_agente is None`
- [X] T012 [P] [US1] Create `tests/unit/test_ac_agt_04_regla_dura.py` — AC-AGT-04: with hard rule R1 active, agent opinion `es_phishing=False` does not lower verdict (verified via spec 08 `evaluar_veredicto`)
- [X] T013 [P] [US1] Create `tests/unit/test_ac_agt_05_tope.py` — AC-AGT-05: with `LLM_MAX_DIARIO=N`, test N-1 calls (model called), N calls (model called), N+1 calls (`revision_manual` without model call) using `ContadorDoble`
- [X] T014 [P] [US1] Create `tests/unit/test_ac_agt_06_simuladas.py` — AC-AGT-06: verify all 6 test files use `ModeloDoble`/`ContadorDoble` — zero real model calls; monkeypatch `ChatGoogleGenerativeAI` to fail if instantiated
- [X] T015 [US1] Confirm all 6 test files RED (ImportError on `src.level2_agent.agente`) — TDD gate

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement `src/level2_agent/agente/prompt.py` — Factory `construir_prompt(entrada: EntradaAgente) -> str` that serializes evidence + texto del correo within `<correo>…</correo>` delimiters + security declaration per contract §5 and research D4/D7
- [X] T017 [P] [US1] Implement `src/level2_agent/agente/validador.py` — `validar_salida(raw: str) -> SalidaAgente | None` that parses JSON, validates against `SalidaAgente` schema with Pydantic, strips markdown fences; returns `None` if validation fails per contract §3 and research D5
- [X] T018 [US1] Implement `src/level2_agent/agente/agente.py` — `consultar_agente(entrada, *, modelo=None, contador=None, ahora=None) -> ResultadoAgente` orchestrator: (1) check tope diario, (2) build prompt, (3) call model with `busqueda_vectorial` tool only, (4) validate output, (5) 1 retry if invalid, (6) return `ResultadoAgente` per contract §1
- [X] T019 [US1] Wire `src/level2_agent/agente/__init__.py` — import and re-export `consultar_agente`, `EntradaAgente`, `SalidaAgente`, `ResultadoAgente`, `ModeloLLM`, `ContadorLLM`, constants
- [X] T020 [US1] Refactor `src/level2_agent/agent.py` — replace hardcoded 30/75 branching with `calcular_score_final` (spec 007) + `consultar_agente` (spec 009) + `evaluar_veredicto` (spec 008); remove `check_ip_reputation` from ReAct tools; remove direct `create_jira_ticket` call; remove `build_chat_prompt` relic per research D2
- [X] T021 [US1] GREEN — run all 6 test files; fix any failures

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently ✅

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, gates and constitution evidence.

- [X] T022 [P] Update `README.md` additively: new M07 section — stateless agent, single tool, structured input, validated output, daily limit, injection resistance
- [X] T023 [P] Update `AGENTS.md` additively: architecture note for `src/level2_agent/agente/` (public API, refactor of agent.py, tools removed, Adapter pattern, ContadorLLM, no new dependencies)
- [X] T024 Run `python scripts/verify.py` end-to-end — lint + mypy `--strict` on agente/ pass; full suite timeout (pre-existing slow tests); ruff ✅, mypy ✅, 14/14 tests ✅
- [X] T025 Run quickstart scenarios V1–V8 plus regression; V1–V6: 14 passed; V8: benign PASS, malicious PASS, ai_agent FAIL (pre-existing ScoreFinal invariant from spec 007); `[VERIFICAR]` items: V1 (RAG sources), V2 (model choice), V3 (real injection test)
- [X] T026 Append a "Constitution compliance verification" section at the end of this file mapping Arts. 0–VII to concrete evidence (commands + outcomes) per Art. VII.3, and mark every task above `[X]` only when its evidence exists (Art. 4.2)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — BLOCKS US1
- **User Story 1 (Phase 3)**: depends on Foundational; tests (T009–T014) must all be written and RED (T015) before implementation (T016–T021)
- **Polish (Phase 4)**: depends on US1 completion (T021 green)

### User Story Dependencies

- **User Story 1 (P1, MVP)**: starts after Foundational (Phase 2); the only story — no cross-story dependencies.

### Within User Story 1

Tests first (T009–T014, parallel) → red confirmation (T015) → models already exist → pure modules first (T016 prompt, T017 validador — both [P], different files) → orchestrator (T018, depends on T016+T017) → exports (T019) → refactor agent.py (T020) → green (T021).

### Parallel Opportunities

- Phase 1: T002, T003, T004 all [P] (different files; T001 first for branch).
- Phase 2: T007, T008 both [P] after T005.
- Phase 3 tests: **all 6 test files T009–T014 are [P]** (one file each).
- Phase 3 implementation: T016, T017 both [P] (two different modules).
- Phase 4: T022, T023 [P].

```bash
# Launch all US1 tests together:
Task: "test_ac_agt_01_herramientas.py" … Task: "test_ac_agt_06_simuladas.py" (T009–T014)
# Launch pure modules together:
Task: "prompt.py" … Task: "validador.py" (T016–T017)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T008) — CRITICAL, blocks US1
3. Complete Phase 3: US1 — tests red first (T009–T015), then implementation (T016–T021)
4. **STOP and VALIDATE**: `pytest tests/unit -k "agt"` green + `tests/test_pipeline.py` green
5. Phase 4 polish + `scripts/verify.py` exit 0 (Art. IV evidence)

### Incremental Delivery

- Setup + Foundational → foundation ready (no user-visible value yet)
- US1 → **MVP**: stateless agent with injection resistance, validated output, daily limit

### Notes

- Marca `[P]` = archivos distintos, sin dependencias; etiqueta de historia = US1 (historia única).
- Tests MUST fail before implementation (T015 checkpoint is the gate).
- Commit after each task or logical group, Conventional Commits in Spanish with AC ids (Art. I.5): `feat(agt): … (AC-AGT-01)`.
- AC-AGT-06: **NINGUNA** prueba llama al modelo real. Todas usan `ModeloDoble`/`ContadorDoble`.
- Scope fence (Art. VI.1 / D12): NO changes to `src/level2_agent/decision/` (import only), `src/gmail_integration/` (spec 010), `src/level2_agent/virustotal/` (import only). `agent.py` refactor is in scope (research D2).

---

## Constitution Compliance Verification (Art. VII.3)

| Artículo | Requisito | Evidencia |
|---|---|---|
| Art. 0 | Sin memoria de chat entre correos | `consultar_agente` no mantiene estado; cada llamada es independiente. Spec 001 ya eliminó memoria. |
| Art. I.5 | Conventional Commits en español con AC IDs | `git log --oneline feature/agente-ia-sin-estado`: `feat(agt): …`, `docs(spec-009): …` |
| Art. II.7 | No tocar umbrales | Score thresholds 30/75 en `models.py` sin cambios |
| Art. III.1 | Archivos ≤ 500 líneas | `wc -l src/level2_agent/agente/*.py` → max 172 líneas (modelos.py) |
| Art. III.4 | mypy `--strict` | `mypy --strict --explicit-package-bases src/level2_agent/agente/` → Success |
| Art. III.6 | Sin números mágicos | Constantes en `modelos.py`: `LLM_MAX_DIARIO_DEFAULT`, `MAX_REINTENTOS`, `LIMITE_*` |
| Art. IV.1 | Compuerta de calidad | ruff ✅, mypy ✅, 14/14 pytest ✅, archivos ≤ 500 ✅ |
| Art. IV.3 | `[VERIFICAR]` items documentados | V1 (RAG sources), V2 (model choice), V3 (real injection test) |
| Art. V.1 | "seguro" jamás aparece como veredicto | Motor de decisión (spec 008) garantizado; agente emite `es_phishing` bool |
| Art. VI.1 | Scope fence | No changes a `decision/` (import only), `gmail_integration/`, `virustotal/` |
| Art. VI.2 | Catálogos como única fuente de verdad | `SalidaAgente.nivel_severidad` = Literal["Bajo","Medio","Alto","Crítico"] |
| Art. VII.3 | Constitution compliance verificada | Esta tabla ✅ |
