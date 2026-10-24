# AGENTS.md

PhishGuard-AI: phishing detection pipeline (genetic score → ReAct agent → Gmail actions). Python 3.10+, Windows-primary (README uses `.venv\Scripts\`), but code is cross-platform.

## Commands

Tests use `pytest` (configured in `pyproject.toml`), and `scripts/verify.py` runs the full gate (lint + mypy + tests + coverage + branch checks). The legacy `tests/test_pipeline.py` is a plain PASS/FAIL runner that `sys.exit(0|1)`.

```powershell
# Install
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the full verification suite (lint + types + tests + coverage)
.venv\Scripts\python.exe scripts/verify.py

# Run only the unit tests
.venv\Scripts\python.exe -m pytest tests/unit/

# Run the legacy fixture pipeline (plain runner)
.venv\Scripts\python.exe tests/test_pipeline.py

# Run the Gmail poller (long-running loop, 30s interval)
.venv\Scripts\python.exe src/gmail_integration/gmail_poller.py
```

To run a single fixture: temporarily move the other `tests/fixtures/*.json` files out — the runner globs every `*.json` in `tests/fixtures/` and there is no filter flag.

## Test prerequisites (easy to miss)

`tests/test_pipeline.py` calls `analyze_email()`, which lazily builds the Gemini LLM and (for the `ai_agent` fixture, score 30–75) the ReAct agent + MongoDB vector retriever. Required env in `.env`:

- `GOOGLE_API_KEY` — mandatory for any test run (LLM is built up front in `analyze_email`).
- `MONGODB_ATLAS_CLUSTER_URI` — needed for the `ai_agent` case (RAG retriever); missing it makes that case fail/degrade, not skip.

Optional: `VT_API_KEY`, `JIRA_*`. Tools degrade gracefully when absent (logged warnings, not errors).

## Architecture notes not obvious from filenames

- **Package root is `src/`**, imported as `src.level2_agent...`, `src.level3_logic...`, `src.gmail_integration...`. There is no installed package; scripts rely on `sys.path.insert(0, PROJECT_ROOT)` and `sys.path.insert(0, SRC_DIR)` at the top of `tests/test_pipeline.py` and `gmail_poller.py`. Do not rename `src/` or move modules without updating these inserts — there is no `src/__init__.py` and no editable install.
- **Normalization pipeline** lives in `src/level2_agent/normalizacion/` (spec 002). Public API (imported from the package `__init__`): `normalizar_desde_gmail` / `normalizar_desde_eml` / `normalizar_desde_api` → `EmailData`, plus `enmascarar_para_terceros` / `enmascarar_texto` for PII. The Gmail poller now calls `get_message_raw` + `normalizar_desde_gmail` (the legacy `email_to_emaildata.py` adapter is kept for compatibility but is no longer on the poller path). `EmailData` gained fields (`cabeceras`, `texto_limpio`, `urls`, `adjuntos`, `origen`, `banderas`, `revision_manual`); `htmlBody` is `exclude=True` so it is never persisted. Constants (5 hard limits + flags) are in `normalizacion/limites.py`, PII regexes in `normalizacion/enmascarado.py`.
- **URL analysis module** lives in `src/level2_agent/analisis_urls/` (spec 004, M04b). Public API (package `__init__`): `analizar_urls(email_data, config=None, deps=None) -> ResultadoURLs`, plus `ConfigURLs` / `ConfiguracionError` and `DependenciasURLs` / `dependencias_por_defecto`. It is intentionally **NOT wired** into `agent.py`/the poller (specs 006/007/008 will consume it); it never touches `models.py` or `normalizacion/`. Catalog codes/severities/points are the literal 13 of `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` 5.2 in `modelos.CATALOGO_URL` — never invent weights (`bandera()` copies them). Expansion is SSRF-guarded **per hop** (`ssrf.py`: FR-004 networks + `is_global`/multicast), capped at `TOPE_SALTOS=5` / `TIMEOUT_URL_SEGUNDOS=5.0` (injected clock), and never reads response bodies. Config env vars (comma-separated, defaults in `configuracion.py`/research D8): `ACORTADORES`, `TLD_RIESGO`, `PARAMETROS_TRACKING`, `PARAMETROS_SENSIBLES` (the 7 literal FR-007 names), `URL_SUBDOMINIOS_MAX`. Tests use doubles from `tests/unit/dobles_red.py` (fake DNS/HTTP/clock + loopback server) — zero real network.
- **Pipeline thresholds** live in `src/level2_agent/models.py`: `SCORE_UMBRAL_BAJO=30`, `SCORE_UMBRAL_ALTO=75`, `SCORE_FALLBACK=50.0`. `analyze_email()` branches on these. The test runner duplicates the 30/75 literals in `detect_route()` — keep them in sync.
- **Genetic weights are hardcoded** in `src/level3_logic/genetic_logic.py` (`PESOS_AG`, 32 genes). `data/genes.xlsx` / `data/Tabla de genes...` are the source spreadsheets, **not loaded at runtime** — editing the xlsx does nothing; edit `PESOS_AG`/`MAPEO_INDICES` in code.
- **LLM model strings are hardcoded**: `models/gemini-2.5-flash-lite` (chat) in `agent.py`, `models/gemini-embedding-001` (embeddings) in `tools/__init__.py`. Not env-driven.
- **MongoDB namespaces** are constants in `models.py`: vector store `phishguard.docs_phishing` (index `vector_index`). The README's "create collection `docs_phishing`" refers to this namespace. There is NO chat-history memory since spec 001 (`refactor/eliminar-memoria`): each email analysis is independent.
- **Jira integration** hardcodes project key `SCRUM` and issuetype `Task` in `tools/jira_integration.py`. Only triggers when `report.es_phishing` is true **and** all `JIRA_*` env vars are set.
- **Gmail OAuth**: `credenciales.json` (OAuth desktop creds) at repo root → first poller run opens browser and writes `token.json`. Both are gitignored. Poller moves phishing to label `"Phishing Alertas"` (created/assumed to exist in Gmail).

## Conventions / gotchas

- `.env` is loaded via `python-dotenv` independently in `agent.py`, `gmail_poller.py`, and `test_pipeline.py`. Each entrypoint loads its own — don't assume a central config module.
- All user-facing strings, prompts, and report fields are in **Spanish**. Preserve language when editing `prompts.py`, report generators in `agent.py`, or fixture `_test` metadata.
- `EmailData.headers` is a **JSON string**, not a dict (see `models.py` / `email_to_emaildata.py`). Genetic logic parses it.
- `notebooks/` are exploratory (gene extraction, AG tuning); `_read_nb.py` is a stdin helper that prints notebook cells. `workflow/` holds the architecture diagram. None of these are part of the runtime pipeline.
- There is no formatter, but **ruff + mypy (`--strict`) are configured** in `pyproject.toml` and enforced by `scripts/verify.py` (which also runs `pytest tests/unit/` with branch coverage and a `--cov-fail-under` gate). `hypothesis` is pinned in `requirements.txt` for property-based tests. Match existing style (4-space indent, Spanish docstrings/logs, `Optional` global singletons for lazy init in `agent.py`).
