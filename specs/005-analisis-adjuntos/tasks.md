---
description: "Task list for Análisis Estático de Adjuntos"
---

# Tasks: Análisis Estático de Adjuntos

**Input**: Design documents from `/specs/005-analisis-adjuntos/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/adjuntos-api.md](./contracts/adjuntos-api.md)

**Tests**: SÍ — la constitución (Art. II.1, II.6) exige TDD con rojo confirmado y trazabilidad AC→prueba. Los tests se escriben ANTES de la implementación.

**Organization**: La spec 005 tiene **una sola historia de usuario (US1, P1)**: analizar estáticamente cada adjunto en memoria (hashes, tipo real por firma, extensiones, Office, PDF, zip con límites) produciendo las banderas del catálogo 5.3, sin ejecutar ni escribir a disco. Las fases reflejan esa estructura: Setup → Fundacional → US1 (tests rojos → implementación por familia) → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (igual que las specs 002/003)

## Testing approach (derived from constitution)

- TDD **rojo primero** (Art. II.1): se escriben todos los tests de US1 y se confirma que fallan antes de implementar.
- Técnicas (research D11): valores límite (obligatorio: 99/100/101 de relación, 100/101 entradas, tope 100 MiB, 0 bytes), tabla de decisión (obligatorio: extensión × firma × content-type), partición de equivalencia (familias de archivo), propiedades con `hypothesis`, seguridad/AST (AC-ADJ-05), regresión (`test_pipeline.py`).
- Cada test de escenario lleva `@pytest.mark.ac("AC-ADJ-NN")` (Art. II.6).
- Archivos maliciosos de prueba (EICAR, zip bomb, ejecutable) **se generan en memoria**, nunca se guardan en el repo (SC-003, Art. 0.5).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias nuevas, esqueleto del paquete, configuración y compuertas

- [x] T001 Add `filetype==1.2.0`, `oletools==0.60.2` and `pypdf==6.21.2` with pinned exact versions to `requirements.txt` (under an `# Analisis de adjuntos (spec 005)` section) and install them into `.venv` (research D3/D6/D7)
- [x] T002 [P] Create package skeleton `src/level2_agent/adjuntos/__init__.py` (empty placeholder so `src.level2_agent.adjuntos` imports) per plan.md structure
- [x] T003 [P] Extend `.env.example` documenting the M05 config vars `ADJ_EXTENSIONES_RIESGO`, `ADJ_EXTENSIONES_HTML`, `ADJ_EXTENSIONES_DOCUMENTO`, `ADJ_LIMITE_ENTRADAS_ZIP`, `ADJ_LIMITE_DESCOMPRIMIDO_ZIP`, `ADJ_RATIO_MAXIMO_ZIP` and `VT_UPLOAD_UNKNOWN=false` (defaults documented, placeholders only, no secret values — Art. V.3; `VT_UPLOAD_UNKNOWN` documents FR-007, its code belongs to spec 006)
- [x] T004 [P] Extend `scripts/verify.py` (RUTAS_CALIDAD_SRC + `--cov=src/level2_agent/adjuntos`) and `pyproject.toml` mypy strict override to include `src/level2_agent/adjuntos` (same mechanism as specs 002/003 — extend scope, do NOT lower thresholds)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el vocabulario compartido (modelos, catálogo, constantes), la configuración y los generadores de prueba en memoria que toda la historia necesita. **BLOCKS all of US1.**

- [x] T005 Create `src/level2_agent/adjuntos/modelos.py` with: `CATALOGO_ADJUNTOS` (transcription literal of the 9 `ADJ_*` codes of catalog 5.3 with their severity/points — Art. VI.2, source of truth; `VT_ADJ_SOSPECHOSO` documented as spec-006-only, never emitted here), constants `ADJ_LIMITE_ENTRADAS_ZIP = 100`, `ADJ_LIMITE_DESCOMPRIMIDO_ZIP = 100 * 1024 * 1024`, `ADJ_RATIO_MAXIMO_ZIP = 100`, `EXTENSIONES_RIESGO_DEFAULT` (exe,scr,com,msi,dll,js,vbs,ps1,bat,cmd,hta,wsf,lnk,iso,img,vhd — literal from M05), `EXTENSIONES_HTML_DEFAULT` (html,htm,svg), `EXTENSIONES_DOCUMENTAL_DEFAULT` (design default per research D4); `Protocol` `Detector` (`evaluar(ctx: ContextoAdjunto) -> ResultadoDetector`), internal `@dataclass(frozen=True)` `ContextoAdjunto` (nombre, extension_final, extensiones_previas, tipo_real, tipo_declarado, payload, config) and `ResultadoDetector`; Pydantic `BanderaAdjunto` (`codigo` in catalog, `severidad` `Literal["media","alta"]` copied from catalog, `puntos` `ge=0`, `detalle` non-empty and **must cite extensions/types, never full filenames or email addresses** — Art. V.4) and `AnalisisAdjunto` (`nombre`, `tipo_declarado`, `tipo_real`, `tamano_bytes` `ge=0`, `sha256` `pattern=r"^[0-9a-f]{64}$"`, `md5` `pattern=r"^[0-9a-f]{32}$"`, `sha1` `pattern=r"^[0-9a-f]{40}$"`, `banderas` ordered by catalog without duplicate codes, `detalles: list[str]`). Docstrings on all public API (Art. III.4)
- [x] T006 [P] Create `src/level2_agent/adjuntos/configuracion.py` with Pydantic `ConfigAdjuntos` (fields `extensiones_riesgo`, `extensiones_html`, `extensiones_documental` as `frozenset[str]`; `limite_entradas_zip`, `limite_descomprimido_zip`, `ratio_maximo_zip` as `int`), `ConfiguracionError`, `defecto()` and `desde_entorno()` reading the 6 `ADJ_*` env vars (comma-separated lists, lowercased, no leading dot; integers `gt=0`). Defaults per research D4/D8/D10 (100 / 104857600 / 100 and the three extension sets). Invalid format (non-numeric integer, limit ≤ 0) → `ConfiguracionError` (Art. III.9). Unit tests construct `ConfigAdjuntos` directly, never touching env (Art. II.5)
- [x] T007 [P] Create `tests/unit/vector_eicar.py` (helper module, NOT a test): `generar_eicar() -> bytes` building the standard 68-byte EICAR test string **in memory** (never a file on disk — SC-003) and constant `EICAR_SHA256` with the **published** hash of the string (research D9: a hardcoded published constant, NOT computed at runtime — a computed expectation would make the test circular)
- [x] T008 [P] Add in-memory attachment fixture helpers to `tests/unit/conftest.py`: builders (returning `bytes`, nothing written to disk — SC-003) for a benign PDF, a PDF containing `/OpenAction`, `/JavaScript` and `/Launch` tokens, a truncated PDF, an OOXML docx (zip) with `word/vbaProject.bin`, a docx with a `*.rels` containing `TargetMode="External"`, a benign docx, a normal zip, an encrypted zip (flag bit 0x1), a zip with N entries, a zip bomb at an exact compression ratio (tunable mix of seeded-PRNG incompressible bytes + zeros — no uncontrolled randomness, Art. II.5), and raw MZ/PE executable bytes

**Checkpoint**: modelos, configuración, EICAR y fixtures en memoria listos — US1 puede empezar.

---

## Phase 3: User Story 1 — Análisis estático seguro de adjuntos (Priority: P1) — MVP

**Goal**: para cada adjunto, producir en memoria los tres hashes (SHA-256/MD5/SHA-1), el tipo real por firma comparado con extensión y `Content-Type`, y las banderas del catálogo 5.3 (extensión de riesgo, doble extensión, HTML/SVG, macro, enlace externo, PDF activo, cifrado, archivo sospechoso) — sin ejecutar, sin escribir a disco y sin red.

**Independent Test**: `pytest tests/unit/ -q` — SHA-256 coincide con referencias publicadas en 3 archivos (AC-ADJ-01); EICAR reconocido por hash y disponible para la spec 006 (AC-ADJ-02); `factura.pdf.exe` → `ADJ_DOBLE_EXTENSION` y exe→`.pdf` → `ADJ_TIPO_NO_COINCIDE` (AC-ADJ-03); zip 101:1 aborta sin agotar memoria (AC-ADJ-04); gate AST + tmpdir vacío, sin escritura ni ejecución (AC-ADJ-05); vacío/truncado/`..`/rutas sin excepción no controlada (AC-ADJ-06).

### Tests for User Story 1 (TDD — write FIRST, must FAIL red) 🔄

> **NOTE**: Estos tests deben escribirse y confirmarse en ROJO (import inexistente o fallos por módulo ausente) ANTES de implementar.

- [x] T009 [P] [US1] Create `tests/unit/test_ac_adj_01_hashes.py` with `@pytest.mark.ac("AC-ADJ-01")`: SHA-256 of 3 test files (empty payload, a fixed text, fixed binary bytes) must equal **published external reference constants hardcoded in the test** (never computed via hashlib at runtime — circular otherwise); MD5 and SHA-1 match their published references too; all three hashes valid lowercase hex of 64/32/40 chars
- [x] T010 [P] [US1] Create `tests/unit/test_ac_adj_02_eicar.py` with `@pytest.mark.ac("AC-ADJ-02")`: `analizar_adjunto("eicar.com", "application/octet-stream", generar_eicar())` produces `sha256 == EICAR_SHA256` (published constant) and `ADJ_EXTENSION_RIESGO` (`.com` ∈ riesgo); asserts `vector_eicar.generar_eicar` is importable from tests for the spec-006 integration test; no EICAR file ever touches disk
- [x] T011 [P] [US1] Create `tests/unit/test_ac_adj_03_extension_tipo.py` with `@pytest.mark.ac("AC-ADJ-03")`: `factura.pdf.exe` carrying MZ bytes → `ADJ_DOBLE_EXTENSION` **and** `ADJ_EXTENSION_RIESGO`; the same MZ executable renamed `factura.pdf` → `ADJ_TIPO_NO_COINCIDE` (conclusive PE signature vs .pdf extension)
- [x] T012 [P] [US1] Create `tests/unit/test_ac_adj_04_zip_bomb.py` with `@pytest.mark.ac("AC-ADJ-04")`: boundary ratios 99:1 and 100:1 → no `ADJ_ARCHIVO_SOSPECHOSO` (in the exact limit there is NO flag — spec-002 convention); 101:1 → abort + `ADJ_ARCHIVO_SOSPECHOSO` with the inspection aborted **during** streamed reading (assert the detector reports abort without materializing the full decompressed size); a zip member lying about its declared size (declares small, decompresses large) is also caught by the hard cap
- [x] T013 [P] [US1] Create `tests/unit/test_ac_adj_05_sin_escritura_ejecucion.py` with `@pytest.mark.ac("AC-ADJ-05")`: (a) AST gate walking every `src/level2_agent/adjuntos/*.py` forbidding any `open(...)` call, imports of `subprocess`, `os.startfile`, `webbrowser`, `shutil`, `requests`, `urllib`, `http`, `socket` (zero disk writes, zero execution, zero network — research D12 + FR-007 scope), and any `Path.write_*`/`Path.unlink`; (b) functional test running the full analysis of every fixture inside `tmp_path` and asserting the directory is **empty** afterwards
- [x] T014 [P] [US1] Create `tests/unit/test_ac_adj_06_entradas_hostiles.py` with `@pytest.mark.ac("AC-ADJ-06")`: empty payload, truncated zip/pdf/ole2 payloads, names with `..`, absolute Windows path `C:\abs\x.pdf`, POSIX path `/etc/passwd`, embedded NUL and RTL-override names — none raises an uncontrolled exception and all produce valid hashes; `hypothesis` properties over arbitrary bytes and names: `analizar_adjunto` never raises, output is deterministic (same input → same result) and hashes stay valid hex (research D11/D14)
- [x] T015 [P] [US1] Create `tests/unit/test_extensiones.py`: the full decision table of data-model.md (rows: benign pdf, exe-firm .pdf → TIPO_NO_COINCIDE, .exe → RIESGO, .pdf.exe → RIESGO+DOBLE, whitespace before extension → DOBLE, .html/.svg → `ADJ_HTML` only, .lnk with unknown firm → RIESGO, .txt → no flag, .docx zip-firm → no flag here, .jpg.exe → RIESGO+DOBLE, .pdf with zip firm → TIPO_NO_COINCIDE), including Content-Type mismatch cases and the conclusive-firm-only rule (unknown firm → no `ADJ_TIPO_NO_COINCIDE` — research D5)
- [x] T016 [P] [US1] Create `tests/unit/test_office.py`: docx with `word/vbaProject.bin` → `ADJ_MACRO`; docx with `TargetMode="External"` rels → `ADJ_ENLACE_EXTERNO`; benign real docx through the real `OlevbaOffice` adapter → no flags (real olevba opens it from memory); the OLE2 macro-found and external-link-found mapping branches covered with a stubbed `VBA_Parser` (monkeypatch — testing OUR mapping, not olevba); any olevba exception degrades to `ADJ_ARCHIVO_SOSPECHOSO` + detalle, never propagates (research D6/D14)
- [x] T017 [P] [US1] Create `tests/unit/test_pdf.py`: PDF with `/OpenAction`, `/JavaScript` and `/Launch` each activate `ADJ_PDF_ACTIVO` (both via raw-byte scan and via the pypdf walk); a compressed-stream PDF hiding the token is still caught by the pypdf path; truncated PDF → `ADJ_ARCHIVO_SOSPECHOSO`; empty payload named `.pdf` → `ADJ_ARCHIVO_SOSPECHOSO`; benign PDF → no flags (research D7)
- [x] T018 [P] [US1] Create `tests/unit/test_comprimidos.py`: encrypted zip → `ADJ_CIFRADO` (content not read); 100 entries OK / 101 entries → `ADJ_ARCHIVO_SOSPECHOSO`; decompressed-size boundary exercised with a reduced `ConfigAdjuntos.limite_descomprimido_zip` (limit is configurable — research D10): at-limit no flag, over-limit → flag + abort; zip ratio handled per AC-ADJ-04; a `.zip`-named payload that is not a valid zip → `ADJ_ARCHIVO_SOSPECHOSO`; a non-zip payload with an unrelated name → detector skips silently (no noise); both-zero-size member → no ratio flag (research D8)
- [x] T019 [US1] Run `pytest tests/unit/ -q` and confirm every US1 test FAILS for the expected reason (red — Art. II.1, e.g. `ModuleNotFoundError: src.level2_agent.adjuntos`); record output

### Implementation for User Story 1

- [x] T020 [P] [US1] Create `src/level2_agent/adjuntos/hashes.py`: pure `calcular_hashes(payload: bytes) -> tuple[str, str, str]` via `hashlib` (SHA-256 principal, MD5 and SHA-1 informativos — FR-001); no I/O (FR-006)
- [x] T021 [P] [US1] Create `src/level2_agent/adjuntos/firma.py`: `detectar_por_firma(payload) -> str` via `filetype` over `io.BytesIO` mapped to internal families (pdf, zip, office-ole, office-ooxml, imagen, ejecutable, html; `"desconocido"` when inconclusive — research D5), and detector comparing firm vs extension family vs `Content-Type` (skip empty content-type; skip when firm unknown) → `ADJ_TIPO_NO_COINCIDE` with detalle naming which comparison failed (FR-002)
- [x] T022 [P] [US1] Create `src/level2_agent/adjuntos/extensiones.py`: pure detector over the name per research D4 decision table — final extension ∈ riesgo → `ADJ_EXTENSION_RIESGO`; ∈ html → `ADJ_HTML`; final ∈ riesgo ∪ html AND a previous extension ∈ documental ∪ riesgo (`factura.pdf.exe`) → `ADJ_DOBLE_EXTENSION`; whitespace right before final extension (regex `\s+\.[^.]+$`, no `os.path`) → `ADJ_DOBLE_EXTENSION` (FR-003)
- [x] T023 [P] [US1] Create `src/level2_agent/adjuntos/office.py`: `AnalizadorOffice` Protocol + `OlevbaOffice` adapter wrapping `oletools.olevba.VBA_Parser` over `io.BytesIO` (macro → `ADJ_MACRO`; external-link indicators → `ADJ_ENLACE_EXTERNO`; ANY exception degrades to `ADJ_ARCHIVO_SOSPECHOSO` + detalle, never propagates — research D6/D14); OOXML path with stdlib `zipfile` over `BytesIO`: `word|xl|ppt/vbaProject.bin` presence → `ADJ_MACRO`, all `*.rels` scanned for `TargetMode="External"` → `ADJ_ENLACE_EXTERNO` (FR-004). Never writes to disk nor opens files — even for olevba (FR-006)
- [x] T024 [P] [US1] Create `src/level2_agent/adjuntos/pdf.py`: detector running (a) raw-byte scan for `/JavaScript`, `/OpenAction`, `/Launch` and (b) `pypdf` read-only walk over `io.BytesIO` (catalog `/Root` → `/OpenAction`, `/Names` → `/JavaScript`, per-page `/AA`); any finding → `ADJ_PDF_ACTIVO`; parse failure with no raw findings → `ADJ_ARCHIVO_SOSPECHOSO` (fallar hacia revisar, Art. V.1 — research D7); empty `.pdf` → `ADJ_ARCHIVO_SOSPECHOSO`
- [x] T025 [P] [US1] Create `src/level2_agent/adjuntos/comprimidos.py`: detector using `zipfile.ZipFile(io.BytesIO(payload))` with **streamed** member reading and a hard cap — abort the instant the accumulated bytes exceed `limite_descomprimido_zip` or the real ratio descomprimido/comprimido exceeds `ratio_maximo_zip` (never trust declared `ZipInfo` sizes — research D8); entry count > `limite_entradas_zip` → abort; encrypted flag bit 0x1 → `ADJ_CIFRADO` (metadata listed, content not read); any abort/invalid-zip-when-indicated → `ADJ_ARCHIVO_SOSPECHOSO`; boundary semantics: in the exact limit NO flag; `compress_size == 0` with `file_size > 0` → infinite ratio → flag; both zero → no flag; one nesting level only (FR-005)
- [x] T026 [US1] Create `src/level2_agent/adjuntos/motor.py`: ordered detector registry (catalog order) and `analizar_adjunto(nombre: str, tipo_declarado: str, payload: bytes, config: ConfigAdjuntos | None = None) -> AnalisisAdjunto` — builds `ContextoAdjunto` once (lowercased extension split via `str.rpartition(".")`, no `os.path`), computes hashes always, runs every detector, deduplicates flags, orders by `CATALOGO_ADJUNTOS` and fills `severidad`/`puntos` from the catalog; NEVER raises by input data (only `ConfiguracionError` at config construction — research D14, contract)
- [x] T027 [US1] Update `src/level2_agent/adjuntos/__init__.py` to export the public API (`analizar_adjunto`, `AnalisisAdjunto`, `BanderaAdjunto`, `ConfigAdjuntos`, `ConfiguracionError`, `CATALOGO_ADJUNTOS`, `ADJ_LIMITE_ENTRADAS_ZIP`, `ADJ_LIMITE_DESCOMPRIMIDO_ZIP`, `ADJ_RATIO_MAXIMO_ZIP`) per contracts/adjuntos-api.md
- [x] T028 [US1] Run `pytest tests/unit/ -q` and confirm all US1 tests are GREEN (red→green); commit each family with Conventional Commits citing its AC (e.g. `feat(adjuntos): deteccion de zip con limites y aborto (AC-ADJ-04)`)

**Checkpoint**: US1 completa e independiente — los hashes, la firma, las extensiones, Office, PDF y el zip con límites producen las banderas del catálogo 5.3 en memoria, sin escritura, sin ejecución y sin red.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: documentación, compuertas y verificación final (Art. IV)

- [x] T029 [P] Update `README.md` to describe the M05 adjuntos module and the test command
- [x] T030 [P] Update `AGENTS.md` with a note on the `adjuntos/` package and the three new pinned dependencies (`filetype`, `oletools`, `pypdf`)
- [x] T031 Run `scripts/check_trazabilidad_ac.py --spec specs/005-analisis-adjuntos/spec.md` and confirm exit 0 (every AC-ADJ-NN has a marked test — Art. II.6)
- [x] T032 Run `pytest tests/unit/ --cov=src/level2_agent/adjuntos --cov-branch --cov-fail-under=80` and confirm ≥ 80% lines and branches on the new package (Art. II.3)
- [x] T033 Run `scripts/verify.py` and confirm exit 0 (ruff, `mypy --strict`, tests with coverage, `check_longitud_archivos`, `check_nombre_rama`, pip-audit; no thresholds lowered). Confirm `tests/test_pipeline.py` still passes (regression, research D11)
- [x] T034 Produce the final report (Art. IV.3): command + test result, coverage % (lines and branches), list of ACs with their test, and any deviation vs the spec; run quickstart.md steps 1–5 (including the `[VERIFICAR]` items of research.md, marked as manual/out-of-CI)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 deps, T002 skeleton) — BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (T005 modelos, T006 config, T007 EICAR, T008 fixtures)
  - Tests T009–T018 first (red) → then implementation T020–T027 (green)
- **Polish (Phase 4)**: Depends on US1 complete

### Within User Story 1

- Tests (T009–T018) MUST be written and FAIL before implementation (T020–T027)
- Detector modules T020–T025 are independent (different files) — parallel
- `motor.py` (T026) depends on all detector modules; `__init__.py` (T027) depends on T026
- Story complete before Polish

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel (different files)
- Foundational: T006, T007, T008 in parallel (T005 is the base, do first)
- US1 tests: T009–T018 all in parallel (different files)
- US1 implementation: T020–T025 all in parallel (different files)
- Polish: T029, T030 in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (red phase):
Task: "test_ac_adj_01_hashes.py"
Task: "test_ac_adj_02_eicar.py"
Task: "test_ac_adj_03_extension_tipo.py"
Task: "test_ac_adj_04_zip_bomb.py"
Task: "test_ac_adj_05_sin_escritura_ejecucion.py"
Task: "test_ac_adj_06_entradas_hostiles.py"
Task: "test_extensiones.py"
Task: "test_office.py"
Task: "test_pdf.py"
Task: "test_comprimidos.py"

# Then launch all detector implementations together (green phase):
Task: "hashes.py"
Task: "firma.py"
Task: "extensiones.py"
Task: "office.py"
Task: "pdf.py"
Task: "comprimidos.py"
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
2. Add US1 (hashes → firma → extensiones → office → pdf → comprimidos → motor) → test independently → **MVP**
3. Polish → compuertas completas → verify.py exit 0 → informe Art. IV.3

### Notes

- [P] tasks = different files, no dependencies
- Cada test de escenario lleva `@pytest.mark.ac("AC-ADJ-NN")` (Art. II.6)
- Commit after each family with Conventional Commits citing its AC (Art. I.5)
- Stop at the US1 checkpoint to validate independently
- Sin IA, sin red, sin escritura a disco, sin ejecución (AC-ADJ-05/FR-006), sin wiring a `agent.py` ni cambios en `models.py` (research D15 — lo consumen specs 006/008)

---

## Phase 5: Convergence

**Purpose**: cerrar brechas detectadas por `/speckit.converge` tras la implementación inicial.

- [x] T035 Add tests for `ConfigAdjuntos.desde_entorno()` and `ConfiguracionError` in `tests/unit/test_configuracion_adjuntos.py`: valid env vars → correct `ConfigAdjuntos`; invalid integer (`ADJ_LIMITE_ENTRADAS_ZIP=abc`) → `ConfiguracionError`; limit ≤ 0 → `ConfiguracionError`; empty env vars → defaults from M05; `ConfiguracionError` is an `Exception` subclass per plan D10, Art. III.9 (partial)
- [x] T036 Fix `src/level2_agent/adjuntos/comprimidos.py:136` to not use `info.filename` in `detalles` — replace `f"entrada {info.filename!r} no legible"` with `"entrada zip no legible"` per research D13, Art. V.4 (detalles must not contain filenames) (contradicts)
- [x] T037 Add test in `tests/unit/test_ac_adj_06_entradas_hostiles.py` asserting no `AnalisisAdjunto.detalles` or `BanderaAdjunto.detalle` contains the attachment's full `nombre` across all fixtures per data-model.md "Validaciones cruzadas" #4 (missing)
- [x] T038 Add targeted tests for uncovered branches: `comprimidos.py:125-136` (streaming read `except` with a corrupt-but-openable zip entry), `office.py:50-53` (olevba `analyze_macros` loop with a stub returning external-link indicator), `firma.py:49-73` (`_familia` branches for office-ole, imagen, html families) per Art. II.3 (partial)
