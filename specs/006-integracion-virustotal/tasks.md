# Tasks: Integración con VirusTotal API v3

**Input**: Design documents from `/specs/006-integracion-virustotal/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: **INCLUDED** — explicitly requested: the spec defines an "Independent Test" per user story, 10 acceptance scenarios marked *Auto*, and the constitution (Art. II.1) mandates tests-first with confirmed red.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Spec 006 has a single user story (US1, P1) → one MVP phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/`, `tests/`, `scripts/` at repository root (plan.md Structure Decision).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and quality-gate wiring for the new package.

- [X] T001 Add `httpx==0.28.1` to `requirements.txt` (única dependencia nueva — research D2), run `pip install -r requirements.txt`, and confirm `python -c "import httpx; print(httpx.__version__)"` succeeds; run `pip-audit -r requirements.txt` and record no high/critical vulnerabilities (Art. III.8)
- [X] T002 [P] Extend `scripts/verify.py` additively: add `src/level2_agent/virustotal` to `RUTAS_CALIDAD_SRC` and to the `pytest --cov=` target so coverage/lint gates measure the new package (same mechanism as specs 002–005 — Art. II.3); do NOT lower any threshold
- [X] T003 [P] Extend `pyproject.toml` additively: strict mypy override for `virustotal.*` (mirror of `analisis_urls.*`/`adjuntos.*`); keep `fail_under` unchanged
- [X] T004 [P] Extend `.env.example` additively with the literal env vars of the plan table 14.x — `VT_TIER=public`, `VT_RPM=4`, `VT_DAILY=500`, `VT_MAX_POR_CORREO=10`, `VT_UPLOAD_UNKNOWN=false`, `VT_SUBMIT_UNKNOWN_URLS=false`, `VT_UMBRAL_MALICIOSA=3`, `VT_UMBRAL_SOSPECHOSA=3`, `VT_UMBRAL_LIMPIA=20` — plus a comment that `VT_API_KEY` goes ONLY here (never in the file committed) and that `public` is demo-only (Art. V.7); NO real secrets

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model/types/ports/doubles shared by every part of US1.

**⚠ CRITICAL**: US1 tests and implementation cannot start until this phase is complete.

- [X] T005 Create `src/level2_agent/virustotal/modelos.py` with: `CATALOGO_VT` — literal transcription of the 5 VT codes of catalogs 5.2/5.3 (Art. VI.2): `VT_URL_SOSPECHOSA` alta/20, `VT_ADJ_SOSPECHOSO` alta/25, `VT_DESCONOCIDO` informativa/0, `VT_NO_DISPONIBLE` informativa/0, `VT_PRESUPUESTO_AGOTADO` informativa/0 (severity/points copied, never computed); constants with their literal values and research D-sources: `TOPE_RPM_PUBLIC=4`, `TOPE_DIA_PUBLIC=500`, `REINTENTOS_MAX=3`, `ESPERA_BASE_SEGUNDOS=1`, `FALLOS_CORTACIRCUITO=5`, `VENTANA_CORTACIRCUITO_SEGUNDOS=60`, `TTL_ARCHIVO_DIAS=7`, `TTL_URL_DIAS=1`, `TTL_DESCONOCIDO_HORAS=1`, `MAX_CONSULTAS_POR_CORREO=10`, `TIMEOUT_CONEXION_SEGUNDOS=3.0`, `TIMEOUT_LECTURA_SEGUNDOS=10.0`, `BASE_VT="https://www.virustotal.com/api/v3"`, `ESPERA_ANALISIS_URL_SEGUNDOS=5`, `UMBRAL_MALICIOSA=3`, `UMBRAL_SOSPECHOSA=3`, `UMBRAL_LIMPIA=20`; Pydantic models per data-model.md: `LastAnalysisStats` (`malicious`/`suspicious`/`harmless`/`undetected` all `int ge=0`; fields missing → 0), `Clasificacion = Literal["maliciosa","sospechosa","limpia","desconocida"]`, `BanderaVT` (`codigo` ∈ `CATALOGO_VT`, `severidad` `Literal["media","alta","informativa"]` copied from catalog, `puntos int ge=0` copied, `detalle` non-empty and NEVER containing the original URL with params, the API key or an email address — Art. V.4/AC-VT-07), `ResultadoVT` (`tipo` `Literal["archivo","url","dominio","ip"]`, `identificador`, `clasificacion`, `fuente` `Literal["red","cache","sin_llamada"]`, `banderas` ordered by `CATALOGO_VT` without duplicate codes, `stats: LastAnalysisStats | None`, `consultas_externas int ge=0 le=1`), `EntradaCache` (frozen dataclass: `clave` format `"{tipo}:{identificador}"`, `clasificacion`, `stats`, `guardada_en`, `expira_en` — all UTC); docstrings on all public API (Art. III.4)
- [X] T006 [P] Create `src/level2_agent/virustotal/configuracion.py` with Pydantic `ConfigVT` and `desde_entorno()` reading `VT_TIER`, `VT_RPM`, `VT_DAILY`, `VT_MAX_POR_CORREO`, `VT_UPLOAD_UNKNOWN`, `VT_SUBMIT_UNKNOWN_URLS`, `VT_UMBRAL_MALICIOSA`, `VT_UMBRAL_SOSPECHOSA`, `VT_UMBRAL_LIMPIA` (research D9): `tier ∈ {public, premium}` else `ConfiguracionError`; `rpm ge=1`; `tope_dia ge=0` (0 = sin tope); `max_por_correo ge=1` else `ConfiguracionError` (contract §5: `VT_MAX_POR_CORREO=0` raises at construction); `upload_unknown` default False and `submit_unknown_urls` default False (Art. V.6); `api_key: str | None` read from `VT_API_KEY`, excluded from `repr` and from any serialization (AC-VT-07); booleans parse `"true"/"1"/"yes"` case-insensitive, anything else → False; Spanish docstring citing that `public` mode is demo-only (Art. V.7)
- [X] T007 [P] Create `src/level2_agent/virustotal/puertos.py` with `Protocol`s per contract §6 — `ClienteHTTPVT` (`async get(path) -> RespuestaVT` with `status: int`, `json: dict`, `headers: Mapping[str, str]`), `RepositorioCacheVT` (`obtener(clave, ahora) -> EntradaCache | None`, `guardar(entrada) -> None`), `RepositorioContadorVT` (`consumir(dia: str) -> bool`, `usos(dia: str) -> int`), `Reloj` (`() -> datetime` UTC), `Dormir` (`async (segundos: float) -> None`), `Jitter` (`() -> float`) — plus `DependenciasVT` dataclass grouping them (Art. III.2) and `dependencias_por_defecto()` returning the production defaults (`httpx.AsyncClient` with `timeout=httpx.Timeout(connect=3.0, read=10.0)` — M06.3; pymongo-backed repos via T027; `datetime.now(UTC)`; `asyncio.sleep`; `random.uniform(0, 1)`)
- [X] T008 [P] Create `tests/unit/dobles_vt.py`: fake `ClienteHTTPVT` built on `httpx.MockTransport` that serves a sequence/map of responses per endpoint and **fails the test if any unregistered request arrives**; recording `Reloj` (advanceable), recording `Dormir` (captures requested seconds, waits 0), `Jitter` returning 0.0; in-memory `RepositorioCacheVT` and in-memory `RepositorioContadorVT` (shareable across instances to simulate a process restart); helper `conectar(config_extra)` building a `ConfigVT` for tests (research D11)
- [X] T009 [P] Create `tests/unit/respuestas_vt/` fixture folder with 3+ recorded/anonymized VT responses as JSON per research D12 — `archivo_maliciosa.json` (200, `last_analysis_stats.malicious=5`), `no_encontrado.json` (404 body), `eicar_maliciosa.json` (200, EICAR hash) — sanitized (no account ids); **NEVER** place VT JSON in `tests/fixtures/` (it would break `tests/test_pipeline.py`, D12)

**Checkpoint**: Foundation ready — US1 can begin.

---

## Phase 3: User Story 1 - Cliente VirusTotal con cuota, caché, reintentos y cortacircuitos (Priority: P1) 🏁 MVP

**Goal**: A deterministic VirusTotal v3 client classifying hashes/URLs/domains/IPs with rate limit, cache, retries, circuit breaker, per-email budget and no upload by default (FR-001..FR-009).

**Independent Test**: With the mocked client and recorded responses, run `pytest tests/unit -k "vt"` — all 10 ACs green with **zero real network**, plus `python tests/test_pipeline.py` regression green.

### Tests for User Story 1 (TDD — write FIRST, confirm RED before implementing) 🔴

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation** (Art. II.1 — red confirmed against a not-yet-existing package; record the red run in the phase checkpoint).

- [X] T010 [P] [US1] Create `tests/unit/test_ac_vt_01_clasificacion.py` with `@pytest.mark.ac("AC-VT-01")`: mocked `GET /files/{sha256}` returning 200 with `malicious=5` → `ResultadoVT.clasificacion == "maliciosa"` and flag `VT_ADJ_SOSPECHOSO` (puntos 25); mocked 404 → `clasificacion == "desconocida"` + flag `VT_DESCONOCIDO`, asserting `!= "limpia"` (G1); no exception raised (G12)
- [X] T011 [P] [US1] Create `tests/unit/test_ac_vt_02_id_url.py` with `@pytest.mark.ac("AC-VT-02")`: 3 known URLs (con path/query, con espacios, con `+` y `=` al final) → each `id_url_base64` matches `^[A-Za-z0-9_-]+$` (no padding), equals `base64.urlsafe_b64encode(u).decode().rstrip("=")`, and the mocked transport receives `GET /urls/{id}`; plus a `hypothesis` property: for arbitrary URLs the id is url-safe, unpadded and idempotent (G2)
- [X] T012 [P] [US1] Create `tests/unit/test_ac_vt_03_cuota.py` with `@pytest.mark.ac("AC-VT-03")`: with `VT_TIER=public` and fake clock, 5 consecutive queries → the transport records ≤ 4 HTTP calls in the first minute (the 5th waits `dormir` with the right seconds or is omitted when `presupuesto` is exhausted — "la quinta espera u se omite"); and with a shared in-memory counter, the 501st call of the day is not sent, then a **new client instance** (simulated restart) still respects the 500/day tope (G3)
- [X] T013 [P] [US1] Create `tests/unit/test_ac_vt_04_reintentos.py` with `@pytest.mark.ac("AC-VT-04")`: (a) 429 with `Retry-After: 7` → next attempt after exactly 7 s (not exponential); (b) 429 without header → waits recorded as 1 s then 2 s then 4 s (+jitter 0) across ≤ 3 retries; (c) 500/502/503 same retry pattern; (d) 404 and 400 → exactly 1 request, no retries; after exhausting retries the result is `desconocida` (G4)
- [X] T014 [P] [US1] Create `tests/unit/test_ac_vt_05_cortacircuito.py` with `@pytest.mark.ac("AC-VT-05")`: 5 consecutive transport failures → circuit opens (60 s fake-clock window with **zero** HTTP calls, `clasificacion=="desconocida"`, flag `VT_NO_DISPONIBLE`, `fuente=="sin_llamada"`); at 59 s still open, at 60/61 s closed again (new call reaches transport); a 200 or 404 in between resets the failure counter (G5, data-model state machine)
- [X] T015 [P] [US1] Create `tests/unit/test_ac_vt_06_cache.py` with `@pytest.mark.ac("AC-VT-06")`: first query hits transport (`fuente=="red"`), second identical query within TTL → `fuente=="cache"` and transport call count unchanged (0 external calls, `consultas_externas==0`, budget NOT consumed — FR-006 "consultas externas"); TTL boundaries per type: file at 6d23h → hit, 7d → miss; URL/domain/IP at 23h → hit, 24h → miss; 404 cached 59min → hit, 60min → miss (G6, FR-005)
- [X] T016 [P] [US1] Create `tests/unit/test_ac_vt_07_saneado_clave.py` with `@pytest.mark.ac("AC-VT-07")`: (a) a URL carrying `token`, `key`, `session`, `email`, `user`, `code`, `password` params and a value shaped like an email arrives at the transport **without them** (delegated to `analisis_urls.sanitizacion.sanitizar_parametros`, research D7); (b) run a full query flow with `VT_API_KEY=supersecreta` and `caplog` capturing all `WARNING+` records → the literal key appears in zero messages (G7)
- [X] T017 [P] [US1] Create `tests/unit/test_ac_vt_08_limites.py` with `@pytest.mark.ac("AC-VT-08")`: classification boundaries — `malicious=2` → not `maliciosa` (→ `sospechosa`), `malicious=3` → `maliciosa`; `suspicious=2` alone with `malicious=0` and low harmless → not `sospechosa` unless the row matches, `suspicious=3` → `sospechosa`; `harmless+undetected=19` → not `limpia`, `=20` (with `malicious=0`, `suspicious<=2`) → `limpia`; budget boundaries — with `VT_MAX_POR_CORREO=10` the 10th external query proceeds, the 11th is not sent and yields flag `VT_PRESUPUESTO_AGOTADO` + `desconocida` (SC-001, SC-003, G8)
- [X] T018 [P] [US1] Create `tests/unit/test_ac_vt_09_sin_subida.py` with `@pytest.mark.ac("AC-VT-09")`: with `VT_UPLOAD_UNKNOWN=false` (default) any call path that could upload an unknown file performs **zero** `POST /files` and zero `POST /urls` (the transport double raises if it ever sees a POST); unknown-file hash with 404 → stays `desconocida` with no upload attempt (G9, Art. V.6)
- [X] T019 [P] [US1] Create `tests/unit/test_ac_vt_10_eicar.py` with `@pytest.mark.ac("AC-VT-10")`: generate EICAR **in memory** via `tests/unit/vector_eicar.py` (spec 005), compute/compare its `sha256`, feed `tests/unit/respuestas_vt/eicar_maliciosa.json` through the mock transport → `clasificacion == "maliciosa"` (G10); assert no EICAR file was written to disk
- [X] T020 [P] [US1] Create `tests/unit/test_clasificacion.py`: full decision table of M06.4/FR-007 on `clasificar_stats` — every row (maliciosa / sospechosa-by-malicious / sospechosa-by-suspicious / limpia / desconocida fallback), including stats entirely missing → `desconocida` (never `limpia`), plus configurable thresholds honored (custom `UmbralesVT` with 2/2/19 changes outcomes) — Art. II.2 decision table
- [X] T021 [P] [US1] Create `tests/unit/test_limitador.py`: token bucket with fake clock — exactly 4 tokens per 60 s window (boundary: at 59 s no refill, at 60 s refill), `VT_RPM` honored in premium, `VT_DAILY=0` disables the daily tope, counter repo `consumir` called once per external query and never for cache hits — Art. II.2 boundary values
- [X] T022 [P] [US1] Create `tests/unit/test_cache_presupuesto.py`: TTL selection per type (file 7 d, url/domain/ip 24 h, 404 → 1 h) written into `EntradaCache.expirada_en` computed from the injected clock; `Presupuesto` semantics — `usar()` returns True exactly `max_por_correo` times then False, 11th request never reaches transport, and two `Presupuesto` instances are independent (no shared state between "emails", Art. II.5)
- [X] T023 [US1] Run `python -m pytest tests/unit -k "vt or clasificacion or limitador or cache_presupuesto"` and **confirm every new test FAILS for the expected reason** (ImportError/ModuleNotFoundError on `src.level2_agent.virustotal` or assertion against missing behavior); record the red output — no implementation exists yet (Art. II.1)

### Implementation for User Story 1

- [X] T024 [P] [US1] Create `src/level2_agent/virustotal/identificadores.py`: `id_url_base64(url: str) -> str` — sanitize first (delegate `sanitizar_parametros` from `src/level2_agent/analisis_urls/sanitizacion.py`, research D7) then `base64.urlsafe_b64encode(...).decode().rstrip("=")`; `dominio_valido(ip_valida)` light shape checks returning `None` (never raising) so malformed indicators reach the client as `desconocida` (G12)
- [X] T025 [P] [US1] Create `src/level2_agent/virustotal/clasificacion.py`: pure `clasificar_stats(stats: LastAnalysisStats | None, umbrales: UmbralesVT) -> Clasificacion` implementing M06.4 literally — `malicious >= umbral_maliciosa (3)` → `maliciosa`; `malicious in (1,2)` OR `suspicious >= umbral_sospechosa (3)` → `sospechosa`; `malicious == 0 and suspicious <= 2 and harmless + undetected >= umbral_limpia (20)` → `limpia`; any other case → `desconocida`; `None`/empty stats → `desconocida` (research D4)
- [X] T026 [P] [US1] Create `src/level2_agent/virustotal/limitador.py`: per-process minute bucket (`TOPE_RPM_PUBLIC=4` per 60 s window on the injected `Reloj`; `VT_RPM` in premium) + daily gate delegating to `RepositorioContadorVT.consumir(dia)` with `VT_DAILY` tope (0 = unlimited); `esperar_si_hay_ficha(...)` uses injected `Dormir` (never `time.sleep`) — research D5
- [X] T027 [P] [US1] Create `src/level2_agent/virustotal/resiliencia.py`: (a) `reintentar(...)` — up to `REINTENTOS_MAX=3` retries on 429/5xx with exponential waits `1, 2, 4` s (+ injected `Jitter`), honoring `Retry-After` (seconds **and** HTTP-date formats) over the exponential value when present; no retry on other 4xx (404 included as terminal result); (b) `Cortacircuito` dataclass — opens after `FALLOS_CORTACIRCUITO=5` consecutive failures for `VENTANA_CORTACIRCUITO_SEGUNDOS=60` s on the injected clock, resets on any 200/404/other-terminal result, no half-open state (research D6/D6b); Spanish docstrings
- [X] T028 [P] [US1] Create `src/level2_agent/virustotal/cache.py`: `ClaveCache(tipo, identificador)` → `"{tipo}:{identificador}"`; `ttl_para(tipo, es_desconocido)` returning 7 d / 24 h / 1 h per FR-005; `CacheMemoria` (in-memory `RepositorioCacheVT` honoring `expira_en` against the injected clock); `CacheMongo` (thin pymongo adapter over collection `vt_cache` with `_id=clave`, `$set` document + `expira_en` field and `expireAfterSeconds=0` TTL index — research D3, index marked `[VERIFICAR]`); failures never raise (Art. III.9)
- [X] T029 [P] [US1] Create `src/level2_agent/virustotal/presupuesto.py`: `presupuesto_nuevo(config) -> Presupuesto` with `restantes` initialized from `VT_MAX_POR_CORREO` (default 10), atomic `usar() -> bool`, `agotado` property; consumption order documented in the module docstring (hashes → URLs con banderas de riesgo → dominios → IPs → demás URLs — M06.3 literal); cache hits never call `usar()` (research D8)
- [X] T030 [US1] Create `src/level2_agent/virustotal/cliente.py`: orchestrator — `consultar_archivo(sha256, *, config, deps, presupuesto)`, `consultar_url(url, *, config, deps, presupuesto, es_riesgosa)`, `consultar_dominio(...)`, `consultar_ip(...)` (all keyword-only, ≤ 5 params, Art. III.2) implementing the flow: validate indicator → cache lookup (no budget) → circuit-breaker gate → daily/minute limiter → budget `usar()` → HTTP GET to `BASE_VT` + `/files/{sha256}` | `/urls/{id}` | `/domains/{d}` | `/ip_addresses/{ip}` with header `x-apikey` built only inside the request function and never logged → `reintentar` → parse `data.attributes.last_analysis_stats` → `clasificar_stats` → flags from `CATALOGO_VT` (`VT_ADJ_SOSPECHOSO` for attachment hash sospechosa/maliciosa, `VT_URL_SOSPECHOSA` for URL sospechosa, `VT_DESCONOCIDO` on 404/error/quota, `VT_NO_DISPONIBLE` on open circuit/missing key, `VT_PRESUPUESTO_AGOTADO` on budget exhaustion); `subir_archivo(...)` and `enviar_url_desconocida(...)` exist but return without building any request while `VT_UPLOAD_UNKNOWN=false` / `VT_SUBMIT_UNKNOWN_URLS=false` (research D13, AC-VT-09); public **sync** API wrapping `asyncio.run` (research D2); all indicator errors modeled as `desconocida` — never an exception to the consumer (G12, Art. III.9); consultation results ordered by input list, not by completion order (research D15)
- [X] T031 [US1] Update `src/level2_agent/virustotal/__init__.py` to export exactly the public API of contracts/virustotal-api.md §1 (`consultar_archivo`, `consultar_url`, `consultar_dominio`, `consultar_ip`, `presupuesto_nuevo`, `clasificar_stats`, `ConfigVT`, `DependenciasVT`, `ResultadoVT`, `BanderaVT`, `LastAnalysisStats`, `Presupuesto`, `CATALOGO_VT`, `ConfiguracionError`, `__all__` sorted) with docstrings in Spanish
- [X] T032 [US1] Run `python -m pytest tests/unit -k "vt or clasificacion or limitador or cache_presupuesto"` and confirm **all red tests from T023 now pass** (green phase), then run the full suite `python -m pytest tests/unit/ -q` — zero failures, zero new skips (Art. IV.1a)

**Checkpoint**: US1 fully functional and independently testable — all 10 ACs green with mocked transport.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, gates and constitution evidence.

- [ ] T033 [P] Update `README.md` additively: new M06 section — what the client does, env vars table, the public/demo license warning (Art. V.7), and the test command
- [ ] T034 [P] Update `AGENTS.md` additively: architecture note for `src/level2_agent/virustotal/` (public API, no wiring into `agent.py`/poller — D14, `vt_cache`/`vt_contador` namespaces, env vars, `httpx` the only new dependency)
- [ ] T035 [P] Run `python scripts/check_trazabilidad_ac.py --spec specs/006-integracion-virustotal/spec.md` and fix any AC-VT-01..10 without a marked test (Art. II.6)
- [ ] T036 Run `python scripts/verify.py` end-to-end until **exit 0** (lint, mypy `--strict`, coverage ≥ 80% lines AND branches on `src/level2_agent/virustotal/`, file lengths ≤ 500, gitleaks, pip-audit, branch name, trazabilité) — Art. IV.1 evidence; fix failures without touching thresholds (Art. II.7)
- [ ] T037 Run quickstart scenarios V1–V11 (`specs/006-integracion-virustotal/quickstart.md` §3) plus regression `python tests/test_pipeline.py`; record outputs and any `[VERIFICAR]` items remaining (Art. IV.3 report)
- [ ] T038 Append a "Constitution compliance verification" section at the end of this file mapping Arts. 0–VII to concrete evidence (commands + outcomes) per Art. VII.3, and mark every task above `[X]` only when its evidence exists (Art. 4.2)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately (T001 first: httpx must install before `puertos.py` imports it in tests)
- **Foundational (Phase 2)**: depends on Setup — BLOCKS US1 (T005 is the base; T006–T009 parallel after T005)
- **User Story 1 (Phase 3)**: depends on Foundational; tests (T010–T022) must all be written and RED (T023) before implementation (T024–T031)
- **Polish (Phase 4)**: depends on US1 completion (T032 green)

### User Story Dependencies

- **User Story 1 (P1, MVP)**: starts after Foundational (Phase 2); the only story — no cross-story dependencies.

### Within User Story 1

Tests first (T010–T022, parallel) → red confirmation (T023) → models already exist → pure modules first (T024 identificadores, T025 clasificacion, T026 limitador, T027 resiliencia, T028 cache, T029 presupuesto — all [P], different files) → orchestrator (T030, depends on T024–T029) → exports (T031) → green (T032).

### Parallel Opportunities

- Phase 1: T002, T003, T004 all [P] (different files; T001 first for httpx).
- Phase 2: T006, T007, T008, T009 [P] after T005.
- Phase 3 tests: **all 13 test files T010–T022 are [P]** (one file each).
- Phase 3 implementation: T024–T029 all [P] (six different modules).
- Phase 4: T033, T034, T035 [P].

```bash
# Launch all US1 tests together:
Task: "test_ac_vt_01_clasificacion.py" … Task: "test_cache_presupuesto.py" (T010–T022)
# Launch all pure modules together:
Task: "identificadores.py" … Task: "presupuesto.py" (T024–T029)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T009) — CRITICAL, blocks US1
3. Complete Phase 3: US1 — tests red first (T010–T023), then implementation (T024–T032)
4. **STOP and VALIDATE**: `pytest tests/unit -k vt` green + `tests/test_pipeline.py` green
5. Phase 4 polish + `scripts/verify.py` exit 0 (Art. IV evidence)

### Incremental Delivery

- Setup + Foundational → foundation ready (no user-visible value yet)
- US1 → **MVP**: deterministic VT client, independently testable (delivers FR-001..FR-009)
- Polish → docs/gates; ready for review/PR (Art. I.6 integration)

### Notes

- Marca `[P]` = archivos distintos, sin dependencias; etiqueta de historia = US1 (historia única).
- Tests MUST fail before implementation (T023 checkpoint is the gate).
- Commit after each task or logical group, Conventional Commits in Spanish with AC ids (Art. I.5): `feat(vt): … (AC-VT-01)`.
- Scope fence (Art. VI.1 / D14): NO changes to `agent.py`, `prompts.py`, `src/gmail_integration/`, `tools/ip_reputation.py`, `normalizacion/`, `analisis_urls/` (import only), `adjuntos/` (data only).
