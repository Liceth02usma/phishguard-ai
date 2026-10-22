# Implementation Plan: Compuertas de Calidad Automáticas

**Branch**: `chore/calidad-base` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/000-calidad-base/spec.md`

## Summary

Dejar el repositorio con compuertas automáticas que fallan cuando se incumple la constitución, ejecutables con un solo comando local y en CI. Se añaden `pyproject.toml` (config de pytest con marker `ac`, ruff, mypy), un script `scripts/verify.py` que orquesta todas las compuertas, scripts individuales por compuerta (longitud de archivos, nombre de rama, trazabilidad AC→prueba, secretos, dependencias), `.pre-commit-config.yaml`, workflow de CI, `.env.example` y `.gitignore` ampliado. Cada script ≤ 500 líneas con sus pruebas.

## Technical Context

**Language/Version**: Python 3.10+ (constitución, Art. III).

**Primary Dependencies**: `pytest`, `pytest-cov`, `ruff`, `mypy`, `pip-audit`, `gitleaks` (vía pre-commit), `pre-commit`. Todas con versión fija (Art. III.8).

**Storage**: N/A (tooling; sin persistencia de aplicación).

**Testing**: `pytest` (meta: pruebas de los propios scripts de compuertas). Técnicas obligatorias: valores límite (AC-CAL-01: 500 vs 501 líneas; AC-CAL-03: cobertura en 79/80 %) y tabla de decisión (AC-CAL-02: conjunto de nombres válidos/inválidos).

**Target Platform**: Windows y Linux (desarrollo local + CI). El comando único DEBE ser cross-platform.

**Project Type**: cli / tooling (scripts de calidad + config).

**Performance Goals**: `python scripts/verify.py` < 2 min en repo limpio (SC-001).

**Constraints**: cada script ≤ 500 líneas y con pruebas (Art. III.1); sin red real en pruebas (Art. II.5); `gitleaks` y `pip-audit` sin hallazgos altos/críticos.

**Scale/Scope**: 7 RF, 6 AC. ~6 scripts pequeños + 4 archivos de config.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Estado | Evidencia |
|---|---|---|
| 0 — Integridad de instrucciones | ✅ | Los archivos de prueba (ej. archivo de 501 líneas para AC-CAL-01) son fixtures tratados como bytes/datos, nunca ejecutados. Ninguna compuerta ejecuta contenido de correos. |
| I — Flujo de ramas | ✅ | Rama `chore/calidad-base` creada y valida `^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$`. Commit Conventional Commits. |
| II — Pruebas primero | ✅ | Pruebas de cada compuerta se escriben antes que el script. Técnicas: valores límite (AC-CAL-01, AC-CAL-03) + tabla de decisión (AC-CAL-02) + par positivo/negativo (AC-CAL-04, AC-CAL-05). ≥3 técnicas. Cobertura ≥80 % del código nuevo. Trazabilidad `@pytest.mark.ac("AC-CAL-NN")`. |
| III — Buenas prácticas | ✅ | Scripts ≤500 líneas, funciones ≤40, `ruff` + `mypy --strict`, umbrales (80, 500, 501) como constantes con nombre, config vía `pydantic-settings`/`pyproject.toml`. |
| IV — Definición de terminado | ✅ | Auto-referente: las compuertas creadas aquí validan esta misma spec. El informe final incluye salida de `verify.py`, cobertura y lista AC→prueba. |
| V — Seguridad y datos | ✅ | RF7: `.gitignore` excluye `.env`, `credenciales.json`, `token.json`. AC-CAL-04: detección de secretos con `gitleaks`. `.env.example` sin valores reales. |
| VI — Simplicidad y alcance | ✅ | Solo compuertas de calidad. FUERA DE ALCANCE: pruebas de negocio, despliegue, contenedores. |
| VII — Gobernanza | ✅ | Esta tabla es la verificación de cumplimiento. Una violación bloquea el avance. |

**Violaciones**: ninguna. Complexity Tracking vacío.

## Project Structure

### Documentation (this feature)

```text
specs/000-calidad-base/
├── plan.md              # este archivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── verify-cli.md    # contrato del comando verify + marker ac
└── tasks.md             # /speckit.tasks (no creado aquí)
```

### Source Code (repository root)

```text
pyproject.toml                  # config de pytest (marker ac), ruff, mypy, cov
.env.example                    # variables sin valores reales
.gitignore                      # ampliado: .env, credenciales.json, token.json, .coverage*, htmlcov/
.pre-commit-config.yaml         # ruff, mypy, gitleaks, pip-audit
.github/
└── workflows/
    └── verify.yml              # ejecuta python scripts/verify.py en cada PR
scripts/
├── verify.py                   # orquestador único: llama a todas las compuertas
├── check_longitud_archivos.py  # RF2: .py ≤ 500 líneas
├── check_nombre_rama.py        # RF3: regex Art. I.2 (excepto main/develop)
├── check_trazabilidad_ac.py    # RF4: informe de AC sin prueba
└── _comunes.py                 # constantes (LIMITE_LINEAS=500, COBERTURA_MIN=80) y helpers
tests/
└── unit/
    ├── test_check_longitud_archivos.py
    ├── test_check_nombre_rama.py
    ├── test_check_trazabilidad_ac.py
    └── conftest.py             # registro del marker ac
```

**Structure Decision**: estructura single-project (Option 1). Los scripts de calidad viven en `scripts/` (no en `src/`, que es código de aplicación). Config centralizada en `pyproject.toml`. Tests en `tests/unit/`. No se añade `src/` ni `backend/`/`frontend/` (fuera de alcance).

## Complexity Tracking

> Sin violaciones de la constitución que justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
