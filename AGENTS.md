# AGENTS.md

PhishGuard-AI: phishing detection pipeline (genetic score → ReAct agent → Gmail actions). Python 3.10+, Windows-primary (README uses `.venv\Scripts\`), but code is cross-platform.

## Commands

There is **no `pytest`, no `pyproject.toml`, no lint/typecheck/CI config**. Tests are plain scripts with a custom PASS/FAIL runner that `sys.exit(0|1)`.

```powershell
# Install
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the verification suite (only test entry point)
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
- **Pipeline thresholds** live in `src/level2_agent/models.py`: `SCORE_UMBRAL_BAJO=30`, `SCORE_UMBRAL_ALTO=75`, `SCORE_FALLBACK=50.0`. `analyze_email()` branches on these. The test runner duplicates the 30/75 literals in `detect_route()` — keep them in sync.
- **Genetic weights are hardcoded** in `src/level3_logic/genetic_logic.py` (`PESOS_AG`, 32 genes). `data/genes.xlsx` / `data/Tabla de genes...` are the source spreadsheets, **not loaded at runtime** — editing the xlsx does nothing; edit `PESOS_AG`/`MAPEO_INDICES` in code.
- **LLM model strings are hardcoded**: `models/gemini-2.5-flash-lite` (chat) in `agent.py`, `models/gemini-embedding-001` (embeddings) in `tools/__init__.py`. Not env-driven.
- **MongoDB namespaces** are constants in `models.py`: vector store `phishguard.docs_phishing` (index `vector_index`), memory `memory-agent.memory`. The README's "create collection `docs_phishing`" refers to this namespace.
- **Jira integration** hardcodes project key `SCRUM` and issuetype `Task` in `tools/jira_integration.py`. Only triggers when `report.es_phishing` is true **and** all `JIRA_*` env vars are set.
- **Gmail OAuth**: `credenciales.json` (OAuth desktop creds) at repo root → first poller run opens browser and writes `token.json`. Both are gitignored. Poller moves phishing to label `"Phishing Alertas"` (created/assumed to exist in Gmail).

## Conventions / gotchas

- `.env` is loaded via `python-dotenv` independently in `agent.py`, `gmail_poller.py`, and `test_pipeline.py`. Each entrypoint loads its own — don't assume a central config module.
- All user-facing strings, prompts, and report fields are in **Spanish**. Preserve language when editing `prompts.py`, report generators in `agent.py`, or fixture `_test` metadata.
- `EmailData.headers` is a **JSON string**, not a dict (see `models.py` / `email_to_emaildata.py`). Genetic logic parses it.
- `notebooks/` are exploratory (gene extraction, AG tuning); `_read_nb.py` is a stdin helper that prints notebook cells. `workflow/` holds the architecture diagram. None of these are part of the runtime pipeline.
- No formatter/linter is configured — match existing style (4-space indent, Spanish docstrings/logs, `Optional` global singletons for lazy init in `agent.py`).
