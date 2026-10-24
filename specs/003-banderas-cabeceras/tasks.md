---
description: "Task list for Banderas Deterministas de Cabeceras y Remitente"
---

# Tasks: Banderas Deterministas de Cabeceras y Remitente

**Input**: Design documents from `/specs/003-banderas-cabeceras/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/banderas-api.md](./contracts/banderas-api.md)

**Tests**: SÍ — la constitución (Art. II.1, II.6) exige TDD con rojo confirmado y trazabilidad AC→prueba. Los tests se escriben ANTES de la implementación.

**Organization**: La spec 003 tiene **una sola historia de usuario (US1, P1)**: producir, para cada correo normalizado, el conjunto de banderas de cabeceras y remitente (catálogo 5.1) con código, severidad, puntos y detalle, sin IA. Las fases reflejan esa estructura: Setup → Fundacional → US1 (tests rojos → implementación por familia) → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (igual que la spec 002)

## Testing approach (derived from constitution)

- TDD **rojo primero** (Art. II.1): se escriben todos los tests de US1 y se confirma que fallan antes de implementar.
- Técnicas (research D10): valores límite (obligatorio), tabla de decisión (obligatorio), partición de equivalencia, dobles de red, regresión, propiedades con `hypothesis`.
- Cada test de escenario lleva `@pytest.mark.ac("AC-HDR-NN")` (Art. II.6).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencia nueva, esqueleto del paquete, configuración y compuertas

- [X] T001 Add `tldextract` with pinned exact version to `requirements.txt` (under a `# Banderas de cabeceras (spec 003)` section) and install it into `.venv` (research D5)
- [X] T002 [P] Create package skeleton `src/level2_agent/banderas/__init__.py` (empty placeholder so `src.level2_agent.banderas` imports) per plan.md structure
- [X] T003 [P] Create `.env.example` documenting the M03 config vars `AUTHSERV_ID`, `DOMINIOS_PROPIOS`, `MARCAS_PROTEGIDAS`, `CONTACTOS_INTERNOS`, `TERMINOS_INTERNOS`, `DOMINIOS_GRATUITOS`, `PROVEEDORES_ENVIO` (placeholders only, no secret values — Art. V.3)
- [X] T004 [P] Extend `scripts/verify.py` coverage measurement and `pyproject.toml` mypy strict override to include `src/level2_agent/banderas` (same mechanism as spec 002 D10 — extend scope, do NOT lower thresholds)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el vocabulario compartido (modelos, catálogo, constantes) y la configuración que toda estrategia necesita. **BLOCKS all of US1.**

- [X] T005 Create `src/level2_agent/banderas/modelos.py` with: `CATALOGO_BANDERAS` (transcription literal of the 16 codes of catalog 5.1 with their severity/points — Art. VI.2, source of truth), constants `TOPE_PUNTOS_BANDERAS = 60`, `UMBRAL_DISTANCIA_EDICION = 2`, `DIAS_CACHE_RDAP = 7`, `TIMEOUT_RDAP_SEGUNDOS = 5`, `DIAS_DOMINIO_NUEVO = 30`, `DIAS_FECHA_FUTURA = 1`, `ANIOS_FECHA_VIEJA = 1`, `MAPA_HOMOGLIFOS`, `REDES_PRIVADAS`; `Protocol` `EvaluadorBandera` (`codigo: str`, `evaluar(ctx) -> BanderaActivada | None`), internal `@dataclass(frozen=True) ContextoEvaluacion`; Pydantic models `BanderaActivada` (`codigo` in catalog, `severidad` `Literal["baja","media","alta","informativa"]`, `puntos` `ge=0`, `detalle` no-empty and **must not contain full email addresses** — Art. V.4), `EstadosAutenticacion` (spf/dkim/dmarc, default `desconocido`), `ResultadoBanderas` (`banderas` ordered by catalog, `estados_autenticacion`, `puntos_totales` with `0 ≤ puntos_totales ≤ TOPE_PUNTOS_BANDERAS`). Docstrings on all public API (Art. III.4)
- [X] T006 [P] Create `src/level2_agent/banderas/configuracion.py` with Pydantic `ConfigBanderas` (fields `authserv_id`, `dominios_propios`, `marcas_protegidas`, `contactos_internos`, `terminos_internos`, `dominios_gratuitos`, `proveedores_envio` as `frozenset[str]`), `ConfiguracionError`, and `desde_entorno()` reading the 7 env vars (comma-separated, lowercased). Defaults per research D9: `authserv_id=""` (conservative → nothing trusted → `AUTH_NO_EVALUABLE`), `dominios_gratuitos` default set (gmail/hotmail/outlook/yahoo/live/icloud/proton.me/protonmail.com), others empty. Invalid format (schemes, `/`, spaces in lists) → `ConfiguracionError` (Art. III.9)
- [X] T007 [P] Add `EmailData` fixtures for banderas tests to `tests/unit/conftest.py`: helper to build `EmailData` with ordered `Cabecera` lists (Authentication-Results, From, Reply-To, Return-Path, Message-ID, Date, Received) plus a canonical phishing-like fixture and a benign one

**Checkpoint**: modelos, configuración y fixtures listos — US1 puede empezar.

---

## Phase 3: User Story 1 — Banderas de cabeceras y remitente deterministas (Priority: P1) — MVP

**Goal**: producir, para cada correo normalizado, las 16 banderas del catálogo 5.1 (código, severidad, puntos, detalle) + estados SPF/DKIM/DMARC + `puntos_totales` con tope 60, sin IA y sin red.

**Independent Test**: `pytest tests/unit/ -q` — cada bandera tiene par positivo/negativo (AC-HDR-01); AR externo ignorado (AC-HDR-02); sin AR confiable → `desconocido` + `AUTH_NO_EVALUABLE` (AC-HDR-03); `paypa1.com` sí / `empresa.com.co` no (AC-HDR-04); suma 61→60 (AC-HDR-05); RDAP caído sin excepción ni puntos (AC-HDR-06).

### Tests for User Story 1 (TDD — write FIRST, must FAIL red) 🔄

> **NOTE**: Estos tests deben escribirse y confirmarse en ROJO (import inexistente o falsos) ANTES de implementar.

- [X] T008 [P] [US1] Create `tests/unit/test_ac_hdr_02_auth_externa.py` with `@pytest.mark.ac("AC-HDR-02")`: an `Authentication-Results` from a non-configured `authserv-id` must NOT set SPF/DKIM/DMARC (states stay `desconocido`, `AUTH_NO_EVALUABLE` active)
- [X] T009 [P] [US1] Create `tests/unit/test_ac_hdr_03_auth_no_evaluable.py` with `@pytest.mark.ac("AC-HDR-03")`: with no trustworthy `Authentication-Results`, spf/dkim/dmarc are `desconocido` and `AUTH_NO_EVALUABLE` fires (never inferred as `pass`)
- [X] T010 [P] [US1] Create `tests/unit/test_autenticacion.py`: decision table (authserv-id matches × method present/absent × result pass/fail/softfail/neutral/none/permerror/temperror); first trusted header wins in physical order; `SPF_FALLA` on fail/softfail, `DKIM_FALLA`/`DMARC_FALLA` on fail; absent method in trusted header → `desconocido` with no flag; permerror/temperror recorded in states but no points
- [X] T011 [P] [US1] Create `tests/unit/test_ac_hdr_04_dominio_parecido.py` with `@pytest.mark.ac("AC-HDR-04")`: `paypa1.com` vs protected `paypal.com` activates `DOMINIO_PARECIDO`; `empresa.com.co` vs `empresa.com` does NOT (organizational-domain comparison, no substring, distance 3)
- [X] T012 [P] [US1] Create `tests/unit/test_dominios.py`: Damerau-Levenshtein/OSA distances 1/2/3 (boundary), homoglyph normalization, punycode `xn--` → `DOMINIO_PARECIDO` and `DOMINIO_PUNYCODE`; `hypothesis` properties (distance symmetric, zero iff equal, ≥ |len a − len b|) per research D5/D6
- [X] T013 [P] [US1] Create `tests/unit/test_ac_hdr_06_rdap_falla.py` with `@pytest.mark.ac("AC-HDR-06")`: RDAP failure/invalid response/timeout/bad-domain raises no exception and activates only `DOMINIO_EDAD_DESCONOCIDA` (0 points, `informativa`)
- [X] T014 [P] [US1] Create `tests/unit/test_rdap.py`: fake `ClienteRDAP` double (no real network); cache hit within 7 days, re-query after TTL; registration < 30 days → `DOMINIO_NUEVO`; 29/30/31-day boundary; failures memoized only within one invocation
- [X] T015 [P] [US1] Create `tests/unit/test_ac_hdr_05_tope_puntos.py` with `@pytest.mark.ac("AC-HDR-05")`: flags summing 61 → `puntos_totales == 60`; flags summing exactly 60 → 60 (boundary values)
- [X] T016 [P] [US1] Create `tests/unit/test_ac_hdr_01_pares_bandera.py` with `@pytest.mark.ac("AC-HDR-01")`: a positive AND negative fixture per each of the 16 codes; plus one canonical full email asserting the exact flag set and total points
- [X] T017 [US1] Run `pytest tests/unit/ -q` and confirm every US1 test FAILS for the expected reason (red — Art. II.1); record output

### Implementation for User Story 1

- [X] T018 [P] [US1] Create `src/level2_agent/banderas/autenticacion.py`: pure RFC 8601 parser (`_parse_authentication_results` → authserv-id + method=result pairs, comments/CFWS stripped) and 4 strategies `SPF_FALLA`, `DKIM_FALLA`, `DMARC_FALLA`, `AUTH_NO_EVALUABLE`; computes `EstadosAutenticacion` trusting only the configured `authserv_id` (research D4)
- [X] T019 [P] [US1] Create `src/level2_agent/banderas/dominios.py`: `dominio_organizacional` via `tldextract.TLDExtract(suffix_list_urls=())`, `distancia_edicion` (OSA, in-repo), `normalizar_homoglifos`; strategies `DOMINIO_PARECIDO` (≤2 / homoglyph / punycode) and `DOMINIO_PUNYCODE` (research D5/D6)
- [X] T020 [P] [US1] Create `src/level2_agent/banderas/identidad.py`: strategies `REPLY_TO_DISTINTO`, `RETURN_PATH_DISTINTO`, `NOMBRE_SUPLANTA`, `MESSAGE_ID_DISTINTO` (skip when From domain in `proveedores_envio`), `REMITENTE_EXTERNO_COMO_INTERNO` — domain comparison by organizational domain, config-driven lists (research D14)
- [X] T021 [P] [US1] Create `src/level2_agent/banderas/contexto.py`: strategies `RECEIVED_INCONSISTENTE` (timestamps non-increasing downward OR private/reserved IP in the first external hop via `ipaddress`), `FECHA_ANOMALA` (> `DIAS_FECHA_FUTURA` future or > `ANIOS_FECHA_VIEJA` past vs injected `ahora`), `REPLY_TO_GRATUITO` (research D13/D15)
- [X] T022 [P] [US1] Create `src/level2_agent/banderas/rdap.py`: `ClienteRDAP` protocol, `RequestsRDAP` (`GET https://rdap.org/domain/{dominio}`, `TIMEOUT_RDAP_SEGUNDOS`, domain sanitized by strict regex before composing URL — Art. V.5), 7-day in-memory success cache, `EdadDominio`; strategies `DOMINIO_NUEVO` and `DOMINIO_EDAD_DESCONOCIDA`; `registrar_evento` never raises (research D7)
- [X] T023 [US1] Create `src/level2_agent/banderas/motor.py`: ordered `registry` of all strategies (catalog order), `evaluar_banderas(correo, config=None, ahora=None, cliente_rdap=None) -> ResultadoBanderas`, applies `puntos_totales = min(suma, TOPE_PUNTOS_BANDERAS)` keeping the full flag list (research D8); fills `severidad`/`puntos` from `CATALOGO_BANDERAS`
- [X] T024 [US1] Update `src/level2_agent/banderas/__init__.py` to export the public API (`evaluar_banderas`, `ConfigBanderas`, `ConfiguracionError`, `ResultadoBanderas`, `BanderaActivada`, `EstadosAutenticacion`, `CATALOGO_BANDERAS`, `TOPE_PUNTOS_BANDERAS`, `ClienteRDAP`) per contracts/banderas-api.md
- [X] T025 [US1] Run `pytest tests/unit/ -q` and confirm all US1 tests are GREEN (red→green); commit each family with Conventional Commits citing its AC (e.g. `feat(banderas): parser RFC 8601 y banderas de autenticacion (AC-HDR-02, AC-HDR-03)`)

**Checkpoint**: US1 completa e independiente — las 16 banderas, los estados de autenticación y el tope de 60 funcionan con correo normalizado, sin red y sin IA.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: documentación, compuertas y verificación final (Art. IV)

- [X] T026 [P] Update `README.md` to describe the M03 banderas module and the test command
- [X] T027 [P] Update `AGENTS.md` with a note on the `banderas/` package and the `tldextract` dependency
- [X] T028 Run `scripts/check_trazabilidad_ac.py --spec specs/003-banderas-cabeceras/spec.md` and confirm exit 0 (every AC-HDR-NN has a marked test — Art. II.6)
- [X] T029 Run `pytest tests/unit/ --cov=src/level2_agent/banderas --cov-branch --cov-fail-under=80` and confirm ≥ 80% lines and branches on the new package (Art. II.3)
- [X] T030 Run `scripts/verify.py` and confirm exit 0 (ruff, `mypy --strict`, tests with coverage, `check_longitud_archivos`, `check_nombre_rama`; no thresholds lowered). Confirm `tests/test_pipeline.py` still passes (regression, research D10)
- [X] T031 Produce the final report (Art. IV.3): command + test result, coverage % (lines and branches), list of ACs with their test, and any deviation vs the spec; run quickstart.md steps 1–5

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T002 skeleton) — BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (T005 modelos, T006 config, T007 fixtures)
  - Tests T008–T016 first (red) → then implementation T018–T024 (green)
- **Polish (Phase 4)**: Depends on US1 complete

### Within User Story 1

- Tests (T008–T016) MUST be written and FAIL before implementation (T018–T024)
- Family modules T018–T022 are independent (different files) — parallel
- `motor.py` (T023) depends on all family modules; `__init__.py` (T024) depends on T023
- Story complete before Polish

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel (different files)
- Foundational: T006, T007 in parallel (T005 is the base, do first)
- US1 tests: T008–T016 all in parallel (different files)
- US1 implementation: T018–T022 all in parallel (different files)
- Polish: T026, T027 in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (red phase):
Task: "test_ac_hdr_02_auth_externa.py"
Task: "test_ac_hdr_03_auth_no_evaluable.py"
Task: "test_autenticacion.py"
Task: "test_ac_hdr_04_dominio_parecido.py"
Task: "test_dominios.py"
Task: "test_ac_hdr_06_rdap_falla.py"
Task: "test_rdap.py"
Task: "test_ac_hdr_05_tope_puntos.py"
Task: "test_ac_hdr_01_pares_bandera.py"

# Then launch all family implementations together (green phase):
Task: "autenticacion.py"
Task: "dominios.py"
Task: "identidad.py"
Task: "contexto.py"
Task: "rdap.py"
```

---

## Implementation Strategy

### MVP First (US1 = the whole feature)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks US1)
3. Complete Phase 3: US1 (tests red → implementation green)
4. **STOP and VALIDATE**: `pytest tests/unit/ -q` green + `check_trazabilidad_ac.py` exit 0
5. Run quickstart.md steps 1–5

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 (autenticación → dominios → identidad → contexto → rdap → motor) → test independently → **MVP**
3. Polish → compuertas completas → verify.py exit 0 → informe Art. IV.3

### Notes

- [P] tasks = different files, no dependencies
- Cada test de escenario lleva `@pytest.mark.ac("AC-HDR-NN")` (Art. II.6)
- Commit after each family with Conventional Commits citing its AC (Art. I.5)
- Stop at the US1 checkpoint to validate independently
- Sin IA, sin red en pruebas, sin wiring a `agent.py` (research D11 — lo consumen specs 007/008)

## Phase 5: Convergence

- [X] T032 Alinear los exports del paquete `src/level2_agent/banderas/__init__.py` con el contrato: exportar el protocolo `ClienteRDAP` en `__all__` y revisar los extras (`calcular_puntos`, `ResultadoAutenticacion`) frente a la lista de contracts/banderas-api.md (contradicts)
- [X] T033 Añadir `tests/unit/test_configuracion.py` sin red que cubra `ConfigBanderas.desde_entorno()` (defaults D9 de las 7 variables, listas separadas por coma en minúsculas) y que los formatos inválidos (esquema/URL, `/` en dominios, espacios en listas) lanzan `ConfiguracionError` (T006, plan Art. III.9) (partial)
- [X] T034 Elevar la caché RDAP a nivel de proceso: singleton de `CacheRDAP` con TTL de 7 días compartido entre invocaciones de `evaluar_banderas` (plan: storage — "diccionario en memoria con TTL de 7 dias por proceso"), manteniendo la inyección de `ahora`/`cliente_rdap` y las pruebas sin red (FR-006) (partial)
- [X] T035 Añadir prueba en `tests/unit/test_rdap.py` que monkeypatchee `requests.get` y verifique que `RequestsRDAP` usa `timeout=TIMEOUT_RDAP_SEGUNDOS` (5 s) en cada intento (edge case "RDAP lento", T022) (partial)

## Phase 6: Convergence

- [X] T036 Añadir en `BanderaActivada` un validador de `detalle` que rechace direcciones de correo completas (Art. V.4) y una prueba que afirme la ausencia de PII sobre todos los detalles producidos por los fixtures (T005, data-model: Validaciones cruzadas #4) (missing)
- [X] T037 Añadir propiedad con hypothesis de `puntos_totales == min(sum(puntos), 60)` sobre subconjuntos generados del catalogo 5.1 (data-model: Validaciones cruzadas #2, SC-002) (partial)
- [X] T038 Alinear los objetos internos con el data-model: declarar `EdadDominio` (`fecha_registro: datetime | None`) y renombrar el campo del contexto a `consultar_edad`, manteniendo el comportamiento y las pruebas verdes (data-model: ContextoEvaluacion/EdadDominio, T022) (partial)
