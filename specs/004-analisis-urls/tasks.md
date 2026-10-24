---
description: "Task list for AnÃ¡lisis y ExpansiÃ³n de URLs"
---

# Tasks: AnÃ¡lisis y ExpansiÃ³n de URLs

**Input**: Design documents from `/specs/004-analisis-urls/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/analizar-urls.md](./contracts/analizar-urls.md), [quickstart.md](./quickstart.md)

**Tests**: SÃ â€” la constituciÃ³n (Art. II.1, II.6) exige TDD con rojo confirmado y trazabilidad ACâ†’prueba; el plan incluye 12 archivos de prueba. Los tests se escriben ANTES de la implementaciÃ³n.

**Organization**: La spec 004 tiene **una sola historia de usuario (US1, P1)**: extraer, normalizar, bandear (catÃ¡logo 5.2) y expandir con seguridad SSRF las URLs de un correo. Las fases reflejan esa estructura: Setup â†’ Fundacional â†’ US1 (tests rojos â†’ implementaciÃ³n verde) â†’ Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (igual que las specs 002/003)

## Testing approach (derived from constitution)

- TDD **rojo primero** (Art. II.1): se escriben todos los tests de US1 y se confirma que fallan antes de implementar.
- TÃ©cnicas (research D10): valores lÃ­mite (obligatorio: 4/5/6 saltos, 5 s, 200/201, 30 dÃ­as, 100 000 caracteres), tabla de decisiÃ³n (obligatorio: mÃ¡quina de expansiÃ³n y matriz SSRF), particiÃ³n, propiedades `hypothesis`, dobles con servidor local, regresiÃ³n.
- Cada test de escenario lleva `@pytest.mark.ac("AC-URL-NN")` (Art. II.6).
- **Cero red externa**: dobles de DNS/HTTP + servidor de loopback; reloj falso (Art. II.5).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: checkout de la rama, esqueleto del paquete y compuertas extendidas

- [X] T001 Run `git switch feature/analisis-urls` (rama ya creada en la fase de plan; Art. I.1 â€” el checkout ocurre antes que cualquier cÃ³digo; el directorio estÃ¡ compartido con sesiones paralelas 003/005/015, no se commitea nada de ellas)
- [X] T002 [P] Create package skeleton `src/level2_agent/analisis_urls/__init__.py` (placeholder con docstring para que `src.level2_agent.analisis_urls` importe) per plan.md structure
- [X] T003 [P] Extend `scripts/verify.py` (add `--cov=src/level2_agent/analisis_urls` and the package to `RUTAS_CALIDAD_SRC`) and `pyproject.toml` (add mypy strict override for `analisis_urls.*`) â€” same mechanism as specs 002/003 D10: extend scope, do NOT lower thresholds (aditive edit, shared file â€” research D14)
- [X] T004 [P] Extend `.env.example` documenting the M04b config vars `ACORTADORES`, `TLD_RIESGO`, `PARAMETROS_TRACKING`, `PARAMETROS_SENSIBLES`, `URL_SUBDOMINIOS_MAX` (placeholders only, no secret values â€” Art. V.3; aditive edit, shared file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: vocabulario compartido (modelos, catÃ¡logo 5.2, constantes), configuraciÃ³n y puertos que todo lo demÃ¡s necesita. **BLOCKS all of US1.**

- [X] T005 Create `src/level2_agent/analisis_urls/modelos.py` with: `CATALOGO_URL` (literal transcription of the 13 codes of catalog 5.2 with severity/points â€” Art. VI.2: `URL_TEXTO_DISTINTO_DESTINO` alta/20, `URL_HOST_IP` alta/15, `URL_ACORTADA` media/10, `URL_ARROBA` media/10, `URL_PUNYCODE` media/10, `URL_TLD_RIESGO` baja/5, `URL_SUBDOMINIOS_EXCESIVOS` baja/5, `URL_PUERTO_NO_ESTANDAR` baja/5, `URL_HTTP_SIN_CIFRADO` baja/5, `URL_LARGA` baja/3, `URL_PARAMETROS_SENSIBLES` media/8, `REDIRECCION_EXCESIVA` media/10, `URL_DOMINIO_NUEVO` alta/15 â€” the `VT_*` codes belong to spec 006, NOT here); constants `TOPE_SALTOS = 5`, `TIMEOUT_URL_SEGUNDOS = 5.0`, `UMBRAL_URL_LARGA = 200`, `DIAS_DOMINIO_NUEVO = 30`, `REDES_PROHIBIDAS` (FR-004 literal: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `::1`, `fc00::/7`, `fe80::/10`); Pydantic models per data-model.md: `BanderaURL` (`codigo` in catalog, `severidad` `Literal["baja","media","alta"]`, `puntos` `ge=0` copied from catalog, `detalle` must NOT contain sensitive values nor full email addresses â€” Art. V.4), `ResultadoExpansion` (`estado` `Literal["no_acortadora","reputacion_conocida","expandida","limite_saltos","limite_tiempo","bloqueada_ssrf","esquema_no_permitido","error_controlado"]`, `destino_final`, `saltos` `ge=0` `le=5`, `duracion_ms` `ge=0`, `motivo`), `UrlAnalizada` (`original` preserved verbatim, `normalizada`, `host`, `esquema`, `texto_mostrado`, `es_acortadora`, `url_saneada`, `expansion`, `codigos`), `EstadisticasURLs` (invariant `expandidas + bloqueadas_ssrf + sin_expansion == total`), `ResultadoURLs` (`urls`, `banderas`, `estadisticas`). Docstrings on all public API (Art. III.4)
- [X] T006 [P] Create `src/level2_agent/analisis_urls/configuracion.py` with Pydantic `ConfigURLs` (frozenset fields `acortadores`, `tlds_riesgo`, `parametros_tracking`, `parametros_sensibles`, int `umbral_subdominios` `ge=1`, `tope_saltos`, `timeout_url`), `ConfiguracionError`, and `desde_entorno()` reading `ACORTADORES`, `TLD_RIESGO`, `PARAMETROS_TRACKING`, `PARAMETROS_SENSIBLES`, `URL_SUBDOMINIOS_MAX` (comma-separated). Defaults per research D8/D12: `acortadores` seeded from `SHORTENERS` of `src/level3_logic/genetic_logic.py` (`bit.ly`, `tinyurl`, `goo.gl`, `t.co`); `parametros_sensibles` = FR-007 literal (`token`, `key`, `session`, `email`, `user`, `code`, `password`); `tlds_riesgo`/`parametros_tracking`/`umbral_subdominios=4` = the documented proposals of D8 marked `[VERIFICAR]`. Invalid value (e.g. non-int umbral) â†’ `ConfiguracionError` (Art. III.9)
- [X] T007 [P] Create `src/level2_agent/analisis_urls/puertos.py` with `Protocol`s `ResolvedorDNS` (`resolver(host) -> list[IPv4Address | IPv6Address]`), `ClienteHTTPExpansion` (`solicitar(url) -> RespuestaRedireccion` with `status`, `location`, `ya_leido`), `CacheReputacionURL` (`conoce(url_saneada) -> bool`), `ClienteRDAP` (`antiguedad_dias(dominio) -> int | None`), plus `DependenciasURLs` dataclass (resolvedor, http, cache, rdap, reloj: `Callable[[], float]`), defaults `CacheVacia` (â†’ `False`, research D4), `SinRDAP` (â†’ `None`, research D5), `ResolvedorDNSGetaddrinfo` (stdlib `socket.getaddrinfo`), `ClienteHTTPRequests` (`requests` with `allow_redirects=False`, `HEAD` with fallback to `GET` on 405/501/403, `stream=True` + `close()` without reading the body â€” research D6), and `dependencias_por_defecto()`
- [X] T008 [P] Add `EmailData` fixtures for URL tests to `tests/unit/conftest.py`: helper building `EmailData` with `htmlBody` covering `href`, `src`, `action`, anchor text pairs (`<a href="http://evil.example">https://banco.com</a>`), plain-text URLs, tracking params and duplicates (case/fragment/tracking variants), plus malformed/oversized variants (aditive edit, shared file â€” research D14)

**Checkpoint**: modelos, catÃ¡logo, configuraciÃ³n, puertos y fixtures listos â€” US1 puede empezar.

---

## Phase 3: User Story 1 â€” ExtracciÃ³n, banderas y expansiÃ³n segura de URLs (Priority: P1) â€” MVP

**Goal**: para cada correo, extraer y normalizar sus URLs sin duplicados (conservando la original), activar las 13 banderas del catÃ¡logo 5.2, sanear parÃ¡metros sensibles antes de cualquier consulta externa y expandir solo acortadores con â‰¤5 saltos, â‰¤5 s y validaciÃ³n SSRF por salto, sin descargar cuerpos ni ejecutar JavaScript.

**Independent Test**: `pytest tests/unit/ -q` â€” texto `https://banco.com` vs destino `http://evil.example` â‡’ `URL_TEXTO_DISTINTO_DESTINO` (AC-URL-01); servidor local + DNS a privada â‡’ cero conexiones (AC-URL-02); cadenas de 4/5/6 saltos y reloj 4.9/5.0/5.1 s (AC-URL-03); cero lecturas de cuerpo (AC-URL-04); duplicados tras normalizar â‡’ uno solo (AC-URL-05); `?token=abc&email=a@b.com` saneada al salir (AC-URL-06); vacÃ­a/malformada/100 000 sin excepciÃ³n (AC-URL-07).

### Tests for User Story 1 (TDD â€” write FIRST, must FAIL red) ðŸ”„

> **NOTE**: Estos tests deben escribirse y confirmarse en ROJO (import inexistente o fallos) ANTES de implementar.

- [X] T009 [US1] Create `tests/unit/dobles_red.py`: test doubles harness â€” `ResolvedorDNSDouble` (mapping hostâ†’list of IPs), `ClienteHTTPDouble` (scripted sequence of `RespuestaRedireccion`; any read attempt raises), `reloj_falso()` (advanceable monotonic clock, research D15), and a `servidor_local` context manager starting `http.server` on 127.0.0.1 with request/redirect/body-read counters (loopback only â€” Art. II.5)
- [X] T010 [P] [US1] Create `tests/unit/test_ac_url_01_texto_vs_destino.py` with `@pytest.mark.ac("AC-URL-01")`: anchor with text `https://banco.com` and destination `http://evil.example` activates `URL_TEXTO_DISTINTO_DESTINO` (20 pts); same text and destination domain â†’ flag absent
- [X] T011 [P] [US1] Create `tests/unit/test_ac_url_02_ssrf_privados.py` with `@pytest.mark.ac("AC-URL-02")`: (a) local test server whose DNS double resolves the shortener host to a private IP â†’ `bloqueada_ssrf` and the server received **zero** requests; (b) first hop allowed (public IP double) redirecting to `http://127.0.0.1/x` â†’ second hop blocked, only ONE request total was made, no connection ever attempted to loopback
- [X] T012 [P] [US1] Create `tests/unit/test_ac_url_03_limite_saltos.py` with `@pytest.mark.ac("AC-URL-03")`: chains of 4, 5 and 6 redirects â€” 4 â‡’ `expandida` without `REDIRECCION_EXCESIVA`; 5 â‡’ stops at hop 5 with `limite_saltos` + `REDIRECCION_EXCESIVA`; 6 â‡’ never issues a 6th request (counter == 5) + `REDIRECCION_EXCESIVA`; fake clock crossing 5.0 s â‡’ `limite_tiempo` + flag (boundaries 4.9/5.0/5.1 s)
- [X] T013 [P] [US1] Create `tests/unit/test_ac_url_04_sin_cuerpo.py` with `@pytest.mark.ac("AC-URL-04")`: across all expansion paths the local server logs zero body reads and every `RespuestaRedireccion.ya_leido` stays `False`; response bodies are never consumed (FR-005)
- [X] T014 [P] [US1] Create `tests/unit/test_ac_url_05_dedup.py` with `@pytest.mark.ac("AC-URL-05")`: `HTTPS://Example.COM/a#frag`, `http://example.com/a?utm_source=x` and `http://example.com/a` collapse to ONE `UrlAnalizada` after normalization, with `original` preserving the first-seen raw URL (FR-001) and stable order
- [X] T015 [P] [US1] Create `tests/unit/test_ac_url_06_saneado.py` with `@pytest.mark.ac("AC-URL-06")`: `?token=abc&email=a@b.com` loses `token` and `email` before leaving the external-query boundary; `hypothesis` property â€” for ANY URL, the string received by the HTTP-port double contains no value of the 7 FR-007 params and no email-shaped value (research D10.4)
- [X] T016 [P] [US1] Create `tests/unit/test_ac_url_07_malformadas.py` with `@pytest.mark.ac("AC-URL-07")`: empty string, malformed schemes (`ht!tp://`, `http://`, spaces, bare `///`), and a 100 000-char URL run through `analizar_urls` without any unhandled exception; `hypothesis` property â€” arbitrary strings never raise (research D10.4)
- [X] T017 [P] [US1] Create `tests/unit/test_banderas_url.py`: table test â€” positive AND negative case per each of the 13 codes of `CATALOGO_URL`, asserting `severidad`/`puntos` equal the catalog 5.2 transcription and that no `VT_*` code can ever be emitted (I5); include 200/201-char boundary for `URL_LARGA` and IPv6 host for `URL_HOST_IP`
- [X] T018 [P] [US1] Create `tests/unit/test_expansion.py`: decision table over the state machine of data-model.md â€” host not in shorteners â‡’ `no_acortadora` (zero port calls); cache hit â‡’ `reputacion_conocida` (zero port calls, FR-006); non-http(s) scheme â‡’ `esquema_no_permitido`; connection error/4xx/5xx â‡’ `error_controlado`; success â‡’ `expandida` with `destino_final`; never more than `TOPE_SALTOS` requests (research D9)
- [X] T019 [P] [US1] Create `tests/unit/test_ssrf.py`: matrix over `REDES_PROHIBIDAS` â€” each of the 8 FR-004 networks (IPv4 and IPv6) resolves â‡’ `bloqueada_ssrf` with zero connections; public addresses (8.8.8.8, 93.184.216.34, 2606:4700::) â‡’ allowed; also assert `0.0.0.0`/multicast blocked by the `is_global` rule (research D7)
- [X] T020 [P] [US1] Create `tests/unit/test_sanitizacion.py`: unit properties of `sanitizar_parametros` â€” the 7 FR-007 names removed, email-shaped values removed in any param name, non-sensitive params (`subject`, `id`) preserved, `original` untouched (hypothesis over arbitrary URLs â€” research D10.4)
- [X] T021 [US1] Run `python -m pytest tests/unit/ -k "ac_url or banderas_url or expansion or ssrf or sanitizacion" -q` and confirm every US1 test FAILS for the expected reason (red â€” Art. II.1); record output

### Implementation for User Story 1

- [X] T022 [P] [US1] Create `src/level2_agent/analisis_urls/extraccion.py`: stdlib `html.parser.HTMLParser` subclass extracting `href`, `src`, `action` attributes and **(anchor text, destination) pairs**, plus plain-text URLs from `texto_limpio`/`textBody`; only `http(s)` candidates; returns ordered raw candidates with their displayed text (FR-001, research D2 â€” `normalizacion/extraccion.py` of spec 002 stays untouched)
- [X] T023 [P] [US1] Create `src/level2_agent/analisis_urls/normalizacion.py`: `normalizar_url()` (host lowercase, drop fragment, drop known tracking params per `ConfigURLs.parametros_tracking`) and `deduplicar()` preserving `original` verbatim and first-seen order, producing `UrlAnalizada.url_saneada` via the sanitizer (FR-001/FR-007, AC-URL-05)
- [X] T024 [P] [US1] Create `src/level2_agent/analisis_urls/sanitizacion.py`: `sanitizar_parametros(url, config)` removing the 7 FR-007 params (`token`, `key`, `session`, `email`, `user`, `code`, `password`) and any param value with an email shape; pure function, never mutates the original (FR-007, AC-URL-06)
- [X] T025 [P] [US1] Create `src/level2_agent/analisis_urls/ssrf.py`: `ip_permitida(ip)` â€” `ipaddress.ip_address` checked against `REDES_PROHIBIDAS` AND `is_global` (defense in depth, research D7); `validar_host(host, resolvedor)` resolving via the port and requiring **every** resolved IP to pass; blocked â‡’ `bloqueada_ssrf` before any connection (FR-004, AC-URL-02)
- [X] T026 [P] [US1] Create `src/level2_agent/analisis_urls/banderas.py`: Strategy + Registry with the 13 pure evaluadores of FR-002, each a single rule over `UrlAnalizada` + context (config, `ResultadoExpansion`, `ClienteRDAP`), filling `severidad`/`puntos` from `CATALOGO_URL`; `URL_DOMINIO_NUEVO` active only when `ClienteRDAP.antiguedad_dias(dominio) < 30` (29/30/31 boundary; `None` â‡’ never active â€” research D5); `URL_PARAMETROS_SENSIBLES` from param names on the unsanitized original; `detalle` without sensitive values (Art. V.4); plus `bandera_de_expansion(expansion)` returning `REDIRECCION_EXCESIVA` only for `limite_saltos`/`limite_tiempo` (research D9)
- [X] T027 [US1] Create `src/level2_agent/analisis_urls/expansion.py`: `expandir_acortador(url_saneada, config, deps) -> ResultadoExpansion` â€” only hosts in `config.acortadores` (`no_acortadora` otherwise); `deps.cache.conoce(...)` â‡’ `reputacion_conocida` (FR-006); scheme check (`esquema_no_permitido`); per hop: resolve+validate via `ssrf.py` BEFORE connecting (`bloqueada_ssrf`, zero connections), then `deps.http.solicitar` (HEAD / GET-fallback, no body â€” FR-005/AC-URL-04); â‰¤ `tope_saltos` requests and â‰¤ `timeout_url` seconds measured on `deps.reloj` (D15); 3xx to shortener â‡’ next hop; final destination â‡’ `expandida`; limits â‡’ `limite_saltos`/`limite_tiempo` + `REDIRECCION_EXCESIVA` (research D6/D9)
- [X] T028 [US1] Create `src/level2_agent/analisis_urls/motor.py`: `analizar_urls(email_data, config=None, deps=None) -> ResultadoURLs` â€” pipeline: extraer (T022) â†’ normalizar/deduplicar/sanitizar (T023/T024) â†’ banderas puras (T026) â†’ expandir solo si aplica (T027) â†’ aÃ±adir `bandera_de_expansion` â†’ `EstadisticasURLs`; explicit try/except mapping unexpected URL failures to `error_controlado` (never leaks `requests`/`socket` exceptions â€” AC-URL-07, Art. III.9)
- [X] T029 [US1] Update `src/level2_agent/analisis_urls/__init__.py` to export the public API (`analizar_urls`, `ConfigURLs`, `DependenciasURLs`, `ResultadoURLs`, `UrlAnalizada`, `BanderaURL`, `ResultadoExpansion`, `ConfiguracionError`, `dependencias_por_defecto`, `CATALOGO_URL`, `TOPE_SALTOS`, `REDES_PROHIBIDAS`) per contracts/analizar-urls.md Â§1
- [X] T030 [US1] Run `python -m pytest tests/unit/ -q` and confirm all US1 tests are GREEN (redâ†’green) with no regression in other specs' tests; commit each module family with Conventional Commits citing its AC (e.g. `feat(analisis-urls): expansion con validacion SSRF por salto (AC-URL-02, AC-URL-03)`)

**Checkpoint**: US1 completa e independiente â€” extracciÃ³n sin duplicados, las 13 banderas, el saneado FR-007 y la expansiÃ³n segura (â‰¤5 saltos/5 s, 0 conexiones privadas, 0 cuerpos) funcionan sin IA, sin wiring y sin red externa.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: documentaciÃ³n, compuertas y verificaciÃ³n final (Art. IV)

- [ ] T031 [P] Update `README.md` to describe the M04b `analisis_urls` module and the test command
- [ ] T032 [P] Update `AGENTS.md` with a note on the `analisis_urls/` package and its config vars (aditive edit, shared file)
- [ ] T033 Run `python scripts/check_trazabilidad_ac.py --spec specs/004-analisis-urls/spec.md` and confirm exit 0 (every AC-URL-NN has a marked test â€” Art. II.6)
- [ ] T034 Run `python -m pytest tests/unit/ --cov=src/level2_agent/analisis_urls --cov-branch --cov-fail-under=80` and confirm â‰¥ 80% lines and branches on the new package (Art. II.3)
- [ ] T035 Run `python scripts/verify.py` and confirm exit 0 (ruff, `mypy --strict`, tests with coverage, `check_longitud_archivos` â‰¤500, `check_nombre_rama` against `feature/analisis-urls`; no thresholds lowered). Confirm `python tests/test_pipeline.py` still PASS (regression, research D10.6)
- [ ] T036 Produce the final report (Art. IV.3): command + test result, coverage % (lines and branches), list of the 7 ACs with their test file, and the `[VERIFICAR]` list V1â€“V7 from quickstart.md (umbral subdominios, TLD/tracking defaults, acortadores reales, TOCTOU, tope 60 pts con 003, peor caso 200 acortadores); run quickstart.md steps E1â€“E7

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first (checkout); T002â€“T004 independent of it and parallel between them
- **Foundational (Phase 2)**: Depends on Setup (T002 skeleton) â€” BLOCKS US1
  - T005 is the base (modelos/catÃ¡logo); T006â€“T008 parallel
- **User Story 1 (Phase 3)**: Depends on Foundational (T005 modelos, T006 config, T007 puertos, T008 fixtures)
  - T009 doubles first, then tests T010â€“T020 in parallel (red) â†’ T021 confirms red â†’ implementation T022â€“T026 parallel, T027 after T025/T007, T028 after everything, T029 after T028 â†’ T030 green
- **Polish (Phase 4)**: Depends on US1 complete (T031â€“T032 parallel; T033â€“T036 sequential gate run)

### Within User Story 1

- Tests (T009â€“T021) MUST be written and FAIL before implementation (T022â€“T029)
- Modules T022â€“T026 are independent files â€” parallel
- `expansion.py` (T027) depends on `ssrf.py`, `puertos.py` and `sanitizacion.py`
- `motor.py` (T028) depends on all modules; `__init__.py` (T029) depends on T028
- Story complete before Polish

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel (different files)
- Foundational: T006, T007, T008 in parallel (T005 first)
- US1 tests: T010â€“T020 all in parallel (T009 harness first)
- US1 implementation: T022â€“T026 all in parallel (different files)
- Polish: T031, T032 in parallel

---

## Parallel Example: User Story 1

```bash
# Launch the harness, then all US1 tests together (red phase):
Task: "tests/unit/dobles_red.py"
Task: "test_ac_url_01_texto_vs_destino.py"
Task: "test_ac_url_02_ssrf_privados.py"
Task: "test_ac_url_03_limite_saltos.py"
Task: "test_ac_url_04_sin_cuerpo.py"
Task: "test_ac_url_05_dedup.py"
Task: "test_ac_url_06_saneado.py"
Task: "test_ac_url_07_malformadas.py"
Task: "test_banderas_url.py"
Task: "test_expansion.py"
Task: "test_ssrf.py"
Task: "test_sanitizacion.py"

# Then launch all module implementations together (green phase):
Task: "extraccion.py"
Task: "normalizacion.py"
Task: "sanitizacion.py"
Task: "ssrf.py"
Task: "banderas.py"
```

---

## Implementation Strategy

### MVP First (US1 = the whole feature)

1. Complete Phase 1: Setup (T001 checkout + T002â€“T004)
2. Complete Phase 2: Foundational (CRITICAL â€” blocks US1)
3. Complete Phase 3: US1 (tests red â†’ implementation green)
4. **STOP and VALIDATE**: `pytest tests/unit/ -q` green + `check_trazabilidad_ac.py` exit 0
5. Run quickstart.md steps E1â€“E7

### Incremental Delivery

1. Setup + Foundational â†’ foundation ready
2. Add US1 (extracciÃ³n â†’ normalizaciÃ³n/saneado â†’ SSRF â†’ banderas â†’ expansiÃ³n â†’ motor) â†’ test independently â†’ **MVP**
3. Polish â†’ compuertas completas â†’ verify.py exit 0 â†’ informe Art. IV.3 con V1â€“V7

### Notes

- [P] tasks = different files, no dependencies
- Cada test de escenario lleva `@pytest.mark.ac("AC-URL-NN")` (Art. II.6)
- Commit after each family with Conventional Commits citing its AC (Art. I.5)
- Stop at the US1 checkpoint to validate independently
- Sin IA, sin red externa en pruebas, sin wiring a `agent.py` (research D11 â€” lo consumen specs 006/007/008)
- `models.py`, `normalizacion/`, `agent.py`, `prompts.py` y el poller **sin diff** (research D2/D11)
- Archivos compartidos con ramas paralelas (verify.py, pyproject, conftest, .env.example, README, AGENTS): solo ediciones **aditivas** (research D14)
