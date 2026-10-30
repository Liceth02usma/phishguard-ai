# Implementation Plan: Acciones Idempotentes en Gmail y Jira

**Branch**: `feature/acciones-gmail-jira` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-acciones-gmail-jira/spec.md`

## Summary

Tras el veredicto del motor de decisión (spec 008), código determinista ejecuta
acciones sobre Gmail (etiquetar, archivar, marcar leído) y Jira (crear ticket
por campaña) según una tabla de mapeo veredicto→acciones. Las acciones son
idempotentes (por message_id), soportan modo simulacro (`DRY_RUN=true` por
defecto, Art. V.2), nunca eliminan correos, y registran cada acción ejecutada
o simulada. Adapter pattern para Gmail y Jira permite dobles de prueba sin
servicios reales.

## Technical Context

**Language/Version**: Python 3.11 (repositorio usa 3.10+, sistema 3.11)

**Primary Dependencies**: google-api-python-client (ya instalado), requests (ya instalado), pydantic (ya instalado). **0 dependencias nuevas.**

**Storage**: MongoDB `phishguard.acciones_ejecutadas` (TTL 30d) para idempotencia y auditoría; fallback in-memory.

**Testing**: pytest + hypothesis + dobles de prueba (GmailDoble, JiraDoble). Cero llamadas reales a APIs.

**Target Platform**: Windows (primary), cross-platform

**Project Type**: library (módulo del pipeline PhishGuard)

**Performance Goals**: Acciones síncronas, < 5s por acción individual, timeout configurable.

**Constraints**: Nunca eliminar correos (FR-005). OAuth scopes mínimos (gmail.modify ya concedido). Jira timeout 15s (ya existente). "Seguro" jamás en notificación (Art. V.1).

**Scale/Scope**: 1 acción por veredicto × 1 correo. Máximo ~100 correos/día (limitado por LLM_MAX_DIARIO).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Nota |
|---|---|---|---|
| Art. 0 | Integridad de instrucciones | PASS | Las acciones las decide código determinista, no el modelo (Art. V.2) |
| Art. I.1 | Rama creada primero | PASS | `feature/acciones-gmail-jira` ya existe |
| Art. I.5 | Conventional Commits | PASS | `feat(act): …` |
| Art. II.1 | Pruebas primero | PASS | TDD con dobles |
| Art. II.2 | ≥3 técnicas | PASS | Tabla de decisión (FR-001), partición de equivalencia (veredictos), integración con dobles |
| Art. II.3 | Cobertura ≥80% | PLAN | Objetivo del plan |
| Art. III.1 | Archivos ≤500 líneas | PASS | 6 módulos, cada uno < 200 líneas estimadas |
| Art. III.4 | mypy --strict | PASS | Override en pyproject.toml |
| Art. III.5 | Patrones de diseño | PASS | Adapter (Gmail, Jira), Command (acciones), tabla de datos (veredicto→acciones) |
| Art. III.6 | Sin números mágicos | PASS | Constantes en `modelos.py` |
| Art. V.1 | "seguro" jamás como veredicto | PASS | FR-007 explícito; notificación usa "sin indicadores" |
| Art. V.2 | DRY_RUN por defecto | PASS | FR-002; `ACCIONES_DRY_RUN=true` por defecto |
| Art. VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..007; fuera: persistencia general (spec 011) |

## Project Structure

### Documentation (this feature)

```text
specs/010-acciones-gmail-jira/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── acciones.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/level2_agent/acciones/
├── __init__.py          # Public API: ejecutar_acciones, modelos, adapters
├── modelos.py           # EntradaAcciones, ResultadoAccion, AccionEjecutada, tabla de mapeo
├── tabla.py             # Tabla veredicto→acciones (FR-001), datos puros
├── gmail_adapter.py     # GmailAdapter Protocol + GmailReal (wraps gmail_reader)
├── jira_adapter.py      # JiraAdapter Protocol + JiraReal (wraps jira_integration)
├── huella.py            # Huella de campaña (FR-004): remitente + asunto normalizado + dominios URLs
└── ejecutor.py          # ejecutar_acciones() orquestador

tests/unit/
├── dobles_acciones.py   # GmailDoble, JiraDoble, entrada_acciones_ejemplo()
├── test_ac_act_01_dry_run.py
├── test_ac_act_02_idempotencia.py
├── test_ac_act_03_no_eliminar.py
├── test_ac_act_04_escapar_truncar.py
├── test_ac_act_05_auditoria.py
├── test_ac_act_06_tabla_acciones.py
├── test_ac_act_07_campaña.py
└── test_ac_act_08_resiliencia_jira.py
```

**Structure Decision**: Single project, paquete nuevo `src/level2_agent/acciones/` siguiendo el patrón de specs 003–009. Los adapters envuelven la funcionalidad existente en `gmail_reader.py` y `jira_integration.py` sin modificarlos.

## Complexity Tracking

Sin violaciones a la constitución. Todas las decisiones están alineadas con Arts. 0–VII.
