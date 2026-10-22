# Implementation Plan: Eliminar Memoria Conversacional del Agente

**Branch**: `refactor/eliminar-memoria` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-eliminar-memoria/spec.md`

## Summary

Erradicar la memoria conversacional del agente para que cada correo se analice de forma
independiente: eliminar `src/level2_agent/memory.py` y todo rastro de historial de chat
(importaciones, `session_id`, escrituras, constantes `MEMORY_*`, bloque `MEMORY_TOOL` del
prompt), dejar invocado el agente sin estado (solo evidencia del correo actual), añadir un
script de una sola ejecución (`scripts/eliminar_memoria.py`) con modo simulación por defecto
y confirmación explícita que elimina por lotes las colecciones de historial de MongoDB sin
tocar la base vectorial RAG, y limpiar README/`.env.example`/documentación de textos de
memoria. TDD obligatorio con dobles (nunca contra Atlas en CI) y trazabilidad AC-MEM-01..04.

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10)

**Primary Dependencies**: langchain / langgraph / langchain-google-genai (agente ReAct),
langchain-mongodb + pymongo (RAG y guion de migración), pydantic, python-dotenv; tooling:
pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks

**Storage**: MongoDB Atlas — se ELIMINA la base de historial `memory-agent` (colección
`memory`); se PRESERVA `phishguard.docs_phishing` (índice `vector_index`, RAG)

**Testing**: pytest con `@pytest.mark.ac`, dobles de red (fake de cliente Mongo, agente
ReAct simulado), `--cov --cov-branch` sobre `scripts/`; ruff y `mypy --strict` sobre
`scripts/` y `tests/unit/`

**Target Platform**: Windows local + Linux CI (GitHub Actions `verify.yml`)

**Project Type**: pipeline lib (`src/`) + script de una sola ejecución (`scripts/`)

**Performance Goals**: borrado por lotes tolerante a colecciones con millones de
documentos (borrado incremental, no carga total en memoria)

**Constraints**: pruebas deterministas sin red (Art. II.5); DRY_RUN por defecto en
operaciones con efecto externo (Art. V.2); ningún archivo `.py` > 500 líneas

**Scale/Scope**: ~6 archivos fuente modificados/eliminados en `src/level2_agent/`, 1 script
nuevo, ~6 archivos de prueba nuevos; nada fuera de `specs/001-eliminar-memoria/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS | `refactor/eliminar-memoria` (renombrada antes de escribir código; cumple regex del Art. I.2 y la rama indicada en la spec) |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | commits `feat|fix|refactor|test|chore: ... (AC-MEM-NN)` |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase de pruebas TDD dedicada en tasks.md; rojo verificado antes de implementar |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 5 técnicas justificadas en `research.md` (D7): partición de equivalencia, valores límite (obligatorio: tamaño de lote), tabla de decisión (obligatorio: reglas del script), integración con dobles, regresión |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | Código ejecutable nuevo = `scripts/eliminar_memoria.py` (lo mide la compuerta existente); cambios en `src/` son solo eliminaciones sin lógica nueva (D9). Sin bajar umbrales |
| II.4 | Sin pruebas sin `assert` | PASS | Cada prueba observable (borrado real vs simulado, igualdad de resultados, búsqueda estática) |
| II.5 | Sin red real en pruebas | PASS | Doble de cliente Mongo y agente ReAct simulado; `MONGODB_ATLAS_CLUSTER_URI` eliminada del entorno de la prueba (D7) |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-MEM-01..04")`; verificado con `scripts/check_trazabilidad_ac.py` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica `pyproject.toml` ni pruebas existentes para hacer pasar la spec |
| III.1 | Archivos `.py` ≤ 500 líneas | PASS | `agent.py` ~241 → baja; script nuevo < 200 (estimado) |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Script con funciones pequeñas (`eliminar_por_lotes`, `procesar_coleccion`, `main`) |
| III.3 | Nombres `snake_case` en español sin tildes | PASS | `eliminar_memoria.py`, `eliminar_por_lotes`, `COLECCION_HISTORIAL` |
| III.4 | Tipado estricto, docstrings en API pública | PASS | `mypy --strict` sobre `scripts/`; docstring en cada función pública |
| III.6 | Sin cadenas/umbrales mágicos | PASS | `BASE_HISTORIAL`, `BASE_RAG_PROTEGIDA`, `TAMANO_LOTE` como constantes con nombre |
| III.7 | Una responsabilidad por módulo | PASS | `scripts/eliminar_memoria.py` solo migra datos; la detección de restos de memoria vive en la prueba estática |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` desnudo; errores con mensaje y exit code 1; fallo de conexión informado |
| IV.1a–i | Definición de terminado | PASS | verify.py exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar / sin "seguro" categórico | PASS | El script informa lo que haría; nunca emite veredictos |
| V.2 | Efecto externo con DRY_RUN por defecto | PASS | Simulación por defecto; borrado real solo con `--confirmar` |
| V.3 | Secretos fuera de reposo | PASS | El script solo lee `MONGODB_ATLAS_CLUSTER_URI` de entorno; nada se registra en logs |
| V.4 | Sin PII en logs | PASS | El script solo loguea nombres de base/colección, nunca contenido de correos |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-005; el resto se anota, no se implementa |
| VI.2 | No inventar valores | PASS | Nombres de colecciones tomados del código existente (`models.py`); decisiones de diseño (tamaño de lote, bandera CLI) documentadas en `research.md`, no inventan reglas de dominio |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Inventario de usos de memoria VERIFICADO contra el código (D1); quedan marcados los puntos que dependen de ejecución real (quickstart, validación manual opcional) |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en `tasks.md` |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.
**Re-evaluación post-fase 1**: sin cambios en el alcance; se mantiene PASS en todos los
gates (ver `research.md` D9 sobre cobertura y D8 sobre CI).

## Project Structure

### Documentation (this feature)

```text
specs/001-eliminar-memoria/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── eliminar-memoria-cli.md   # Phase 1 output (contrato del CLI de migración)
├── checklists/
│   └── requirements.md  # checklist de requirements (scaffolding)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── agent.py              # EDITAR: quitar import de memory, chat_history y escrituras
│   ├── memory.py             # ELIMINAR (FR-001)
│   ├── models.py             # EDITAR: quitar MEMORY_DATABASE / MEMORY_COLLECTION (FR-001)
│   └── prompts.py            # EDITAR: quitar MEMORY_TOOL y su inclusión (FR-001/FR-004)
├── gmail_integration/        # SIN CAMBIOS (verificado: sin referencias a memoria)
└── level3_logic/             # SIN CAMBIOS

scripts/
└── eliminar_memoria.py       # NUEVO: script de migración (FR-003)

tests/
├── unit/
│   ├── test_ac_mem_01_codigo_sin_memoria.py   # NUEVO — estático sobre src/ y docs
│   ├── test_ac_mem_02_independencia.py        # NUEVO — dobles del agente
│   ├── test_ac_mem_03_migracion.py            # NUEVO — doble de cliente Mongo
│   ├── test_ac_mem_04_rag_intacto.py          # NUEVO — doble de cliente Mongo
│   └── dobles_mongo.py                        # NUEVO — doble mínimo de pymongo
├── test_pipeline.py          # SIN CAMBIOS (fuera del alcance de compuertas, ver spec 000)
└── fixtures/                 # SIN CAMBIOS

.github/workflows/verify.yml  # EDITAR: instalar requirements.txt para que las pruebas
                              # de src/ corran en CI (D8 — necesario, sin skips)

README.md                     # EDITAR: quitar memory.py del árbol y "memoria conversacional" (FR-004)
AGENTS.md                     # EDITAR: quitar mención a namespace memory-agent.memory (FR-004, doc afectada)
.env.example                  # VERIFICAR: sin variables de memoria (inventario D1: no tiene)
requirements.txt              # SIN CAMBIOS: langchain-mongodb se conserva para el RAG (D3)
```

**Structure Decision**: se conserva la estructura existente (no se mueven paquetes). El
script de migración vive en `scripts/` para que las compuertas de calidad de la spec 000
(ruff, mypy, cobertura sobre `scripts/`) lo cubran automáticamente. Las pruebas de esta
spec van en `tests/unit/` (mismo motivo). No se crea ningún paquete nuevo.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS).
