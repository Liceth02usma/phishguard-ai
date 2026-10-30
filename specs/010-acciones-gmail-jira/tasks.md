# Tasks: Acciones Idempotentes en Gmail y Jira

**Input**: Design documents from `/specs/010-acciones-gmail-jira/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD estricto — las pruebas se escriben ANTES que la implementación y se confirma el rojo. Todos los tests usan `GmailDoble`/`JiraDoble` — cero llamadas reales.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow the pattern of specs 003–009

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estructura del paquete, mypy override y compuertas extendidas.

- [X] T001 Create package `src/level2_agent/acciones/` with empty `__init__.py`, `modelos.py`, `tabla.py`, `gmail_adapter.py`, `jira_adapter.py`, `huella.py`, `ejecutor.py`
- [X] T002 [P] Add mypy strict override for `src.level2_agent.acciones.*` in `pyproject.toml` (same pattern as specs 003–009)
- [X] T003 [P] Extend `scripts/verify.py` coverage to `src/level2_agent/acciones/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos de datos, constantes, tipos, Protocols de adapters y doubles de prueba.

- [X] T004 Create `src/level2_agent/acciones/modelos.py` with `EntradaAcciones` (fields: `veredicto` Literal 4 valores, `nivel_severidad` Literal 4 valores, `message_id` str len≥1, `remitente` str, `asunto` str, `urls` list[str] default [], `reporte` PhishingReport, `origen` Literal["gmail","api"]), `ResultadoAccion` (fields: `accion` Accion enum, `destino` Literal["gmail","jira"], `identificador` str, `ejecutada` bool, `motivo` Literal["exito","dry_run","idempotencia","error_jira","error_gmail"], `timestamp` datetime, `detalle` str|None), `ResultadoAcciones` (fields: `acciones` list[ResultadoAccion], `huella_campaña` str|None, `ticket_key` str|None, `procesado` bool), `Accion` enum (6 valores: ETIQUETAR_PHISHING, ETIQUETAR_REVISAR, ARCHIVAR, MARCAR_LEIDO, CREAR_TICKET, CREAR_TICKET_BAJA), `ResultadoJira` (fields: `exito` bool, `issue_key` str|None, `url` str|None, `error` str|None), constants: `ETIQUETA_PHISHING="Phishing Alertas"`, `ETIQUETA_REVISAR="Revisar Seguridad"`, `DRY_RUN_DEFAULT=True`, `MAX_CHARS_DESCRIPCION_JIRA=3000`, `MAX_CHARS_SUMMARY_JIRA=190`, `HUELLA_LONGITUD=16`, `JIRA_PROYECTO="SCRUM"`, `JIRA_TIPO_TICKET="Task"` per data-model.md
- [X] T005 Create `src/level2_agent/acciones/__init__.py` skeleton exporting public API: `ejecutar_acciones`, `EntradaAcciones`, `ResultadoAccion`, `ResultadoAcciones`, `Accion`, `GmailAdapter`, `JiraAdapter`, constants
- [X] T006 [P] Create `src/level2_agent/acciones/tabla.py` with `resolver_acciones(veredicto: Veredicto) -> list[Accion]` — pure data table per contract §4: `malicioso→[ETIQUETAR_PHISHING, ARCHIVAR, CREAR_TICKET]`, `sospechoso→[ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]`, `revision_manual→[ETIQUETAR_REVISAR, CREAR_TICKET_BAJA]`, `sin_indicadores→[MARCAR_LEIDO]` (FR-001, D3)
- [X] T007 [P] Create `src/level2_agent/acciones/huella.py` with `calcular_huella(remitente, asunto, urls) -> str` — SHA-256(remitente + asunto_normalizado + dominios_ordenados)[:16]; `normalizar_asunto(asunto) -> str` strips RE:/FWD:, lower, collapse whitespace; `extraer_dominios(urls) -> list[str]` extracts registrable domains via tldextract, sorted, deduplicated (FR-004, D6)
- [X] T008 [P] Create `src/level2_agent/acciones/gmail_adapter.py` with `GmailAdapter` Protocol (methods: `etiquetar(msg_id, etiqueta) -> str`, `archivar(msg_id) -> None`, `marcar_leido(msg_id) -> None`, `crear_etiqueta(nombre) -> str`) and `GmailReal` class wrapping `gmail_reader.py` functions per contract §2
- [X] T009 [P] Create `src/level2_agent/acciones/jira_adapter.py` with `JiraAdapter` Protocol (methods: `crear_ticket(campos) -> ResultadoJira`, `buscar_por_huella(huella) -> str|None`, `vincular(key_origen, key_destino) -> None`) and `JiraReal` class wrapping `jira_integration.py` per contract §3; `sanear_texto_jira(texto, *, max_chars=3000) -> str` strips HTML, escapes Jira wiki markup, truncates (AC-ACT-04, D11)
- [X] T010 [P] Create test helper `tests/unit/dobles_acciones.py` with `GmailDoble` (tracks calls in `llamadas` list, returns predefined values), `JiraDoble` (tracks calls, `buscar_por_huella` returns `None` by default, `crear_ticket` returns `ResultadoJira(exito=True, issue_key="TEST-1")`), `entrada_acciones_ejemplo()` factory, `entrada_acciones_ejemplo_por_veredicto(veredicto)` factory

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Acciones por veredicto, idempotentes y en simulacro (Priority: P1) 🏁 MVP

**Goal**: Tras el veredicto final, código determinista ejecuta acciones sobre Gmail y Jira según tabla, con DRY_RUN activo por defecto, idempotencia por message_id, sin eliminar correos, y registrando cada acción.

**Independent Test**: Con dobles de Gmail y Jira, procesar el mismo mensaje dos veces y verificar idempotencia; con DRY_RUN=true, verificar que no se ejecuta ninguna escritura.

### Tests for User Story 1 (TDD — write FIRST, confirm RED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US1] Create `tests/unit/test_ac_act_01_dry_run.py` — AC-ACT-01: with `ACCIONES_DRY_RUN=true`, call `ejecutar_acciones` for each verdict; verify all `ResultadoAccion.ejecutada == False` and `motivo == "dry_run"`; verify `GmailDoble.llamadas` is empty and `JiraDoble.llamadas` is empty
- [X] T012 [P] [US1] Create `tests/unit/test_ac_act_02_idempotencia.py` — AC-ACT-02: call `ejecutar_acciones` twice with same `message_id`; first call executes actions, second call returns `motivo == "idempotencia"` for all actions and `ejecutada == False`; no adapter calls on second invocation
- [X] T013 [P] [US1] Create `tests/unit/test_ac_act_03_no_eliminar.py` — AC-ACT-03: (1) `Accion` enum has no delete/trash/eliminar value; (2) `GmailAdapter` Protocol has no `eliminar` method; (3) AST gate: no file in `acciones/` contains `trash`, `delete` or `eliminar` as identifier
- [X] T014 [P] [US1] Create `tests/unit/test_ac_act_04_escapar_truncar.py` — AC-ACT-04: test `sanear_texto_jira` with HTML tags (`<script>alert(1)</script>`), Jira markup (`{code}rm -rf{code}`, `{color:red}`), 10 000 char string → truncated to 3000 with ellipsis; test summary truncation to 190 chars
- [X] T015 [P] [US1] Create `tests/unit/test_ac_act_05_auditoria.py` — AC-ACT-05: call `ejecutar_acciones` for `malicioso`; verify `ResultadoAcciones.acciones` has 3 items, each with `accion`, `destino`, `identificador`, `ejecutada`, `motivo`, `timestamp` populated; verify `ResultadoAcciones.procesado == True`
- [X] T016 [P] [US1] Create `tests/unit/test_ac_act_06_tabla_acciones.py` — AC-ACT-06: test `resolver_acciones` for all 4 verdicts; verify `malicioso→3 acciones`, `sospechoso→2 acciones`, `revision_manual→2 acciones`, `sin_indicadores→1 acción`; verify exact action types per contract §4
- [X] T017 [P] [US1] Create `tests/unit/test_ac_act_07_campana.py` — AC-ACT-07: two emails with same sender + same normalized subject + same URL domains → same huella; `JiraDoble.buscar_por_huella` returns existing key on second call → second email links to first ticket instead of creating new one; verify only 1 `crear_ticket` call
- [X] T018 [P] [US1] Create `tests/unit/test_ac_act_08_resiliencia_jira.py` — AC-ACT-08: `JiraDoble` configured to raise `ConnectionError` on `crear_ticket`; call `ejecutar_acciones` for `malicioso`; verify Gmail actions executed (`ejecutada=True`), Jira action has `motivo="error_jira"`, no retry, no exception raised
- [X] T019 [US1] Confirm all 8 test files RED (ImportError on `src.level2_agent.acciones`) — TDD gate

### Implementation for User Story 1

- [X] T020 [US1] Implement `src/level2_agent/acciones/ejecutor.py` — `ejecutar_acciones(entrada, *, gmail=None, jira=None, ahora=None) -> ResultadoAcciones` orchestrator per contract §1: (1) check idempotencia (MongoDB `phishguard.acciones_ejecutadas` by message_id, fallback in-memory), (2) check DRY_RUN env var `ACCIONES_DRY_RUN` (default true), (3) resolve actions from tabla, (4) execute each action via adapter, (5) if Jira fails → register error, continue Gmail (D10), (6) register in MongoDB for idempotencia, (7) return ResultadoAcciones; injected clock for determinism
- [X] T021 [US1] Wire `src/level2_agent/acciones/__init__.py` — import and re-export `ejecutar_acciones`, `EntradaAcciones`, `ResultadoAccion`, `ResultadoAcciones`, `Accion`, `GmailAdapter`, `JiraAdapter`, `ResultadoJira`, constants
- [X] T022 [US1] Wire `src/gmail_integration/gmail_poller.py` — replace direct `move_to_label`/`mark_as_read` calls with `ejecutar_acciones` using `VeredictoMotor.veredicto` from the decision engine; construct `EntradaAcciones` from `EmailData` + `VeredictoMotor` + `PhishingReport`; inject `GmailReal` and `JiraReal` adapters; log `ResultadoAcciones`
- [X] T023 [US1] GREEN — run all 8 test files; fix any failures

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, gates and constitution evidence.

- [X] T024 [P] Update `README.md` additively: new M08 section — acciones idempotentes, tabla de mapeo, DRY_RUN, idempotencia, huella de campaña, adapters, sin eliminación
- [X] T025 [P] Update `AGENTS.md` additively: architecture note for `src/level2_agent/acciones/` (public API, wiring in poller, Adapter pattern, tabla de datos, idempotencia MongoDB, DRY_RUN, no new dependencies)
- [X] T026 Run `python scripts/verify.py` end-to-end until **exit 0** (lint, mypy `--strict`, coverage ≥ 80 %, file lengths ≤ 500, gitleaks, pip-audit, branch name, trazabilidad) — Art. IV.1 evidence; fix failures without touching thresholds (Art. II.7)
- [X] T027 Run quickstart scenarios V1–V9 (`specs/010-acciones-gmail-jira/quickstart.md` §2) plus regression `python tests/test_pipeline.py`; record outputs and any `[VERIFICAR]` items remaining (Art. IV.3 report)
- [X] T028 Append a "Constitution compliance verification" section at the end of this file mapping Arts. 0–VII to concrete evidence (commands + outcomes) per Art. VII.3, and mark every task above `[X]` only when its evidence exists (Art. 4.2)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — BLOCKS US1
- **User Story 1 (Phase 3)**: depends on Foundational; tests (T011–T018) must all be written and RED (T019) before implementation (T020–T023)
- **Polish (Phase 4)**: depends on US1 completion (T023 green)

### User Story Dependencies

- **User Story 1 (P1, MVP)**: starts after Foundational (Phase 2); the only story — no cross-story dependencies.

### Within User Story 1

Tests first (T011–T018, parallel) → red confirmation (T019) → pure modules already exist (tabla T006, huella T007, adapters T008–T009) → executor (T020, depends on all foundational) → exports (T021) → wire poller (T022) → green (T023).

### Parallel Opportunities

- Phase 1: T002, T003 both [P] (different files; T001 first for package).
- Phase 2: T006, T007, T008, T009, T010 all [P] after T004/T005.
- Phase 3 tests: **all 8 test files T011–T018 are [P]** (one file each).
- Phase 4: T024, T025 [P].

```bash
# Launch all US1 tests together:
Task: "test_ac_act_01_dry_run.py" … Task: "test_ac_act_08_resiliencia_jira.py" (T011–T018)
# Launch foundational pure modules together:
Task: "tabla.py" … Task: "jira_adapter.py" (T006–T009)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010) — CRITICAL, blocks US1
3. Complete Phase 3: US1 — tests red first (T011–T019), then implementation (T020–T023)
4. **STOP and VALIDATE**: `pytest tests/unit -k "act"` green + `tests/test_pipeline.py` regression
5. Phase 4 polish + `scripts/verify.py` exit 0 (Art. IV evidence)

### Incremental Delivery

- Setup + Foundational → foundation ready (no user-visible value yet)
- US1 → **MVP**: acciones idempotentes con DRY_RUN, tabla de mapeo, auditoría

### Notes

- Marca `[P]` = archivos distintos, sin dependencias; etiqueta de historia = US1 (historia única).
- Tests MUST fail before implementation (T019 checkpoint is the gate).
- Commit after each task or logical group, Conventional Commits in Spanish with AC ids (Art. I.5): `feat(act): … (AC-ACT-01)`.
- AC-ACT-03: **NINGUNA** acción elimina correos. AST gate lo verifica.
- Scope fence (Art. VI.1 / D12): NO changes to `src/level2_agent/decision/` (import only), `src/level2_agent/agente/` (import only), `src/gmail_integration/gmail_reader.py` (wrapped, not modified), `src/level2_agent/tools/jira_integration.py` (wrapped, not modified). `gmail_poller.py` wiring is in scope (D12).
