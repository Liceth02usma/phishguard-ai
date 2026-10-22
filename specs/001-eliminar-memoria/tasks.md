# Tasks: Eliminar Memoria Conversacional del Agente

**Input**: Design documents from `/specs/001-eliminar-memoria/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: INCLUIDAS â€” la spec exige comprobaciones automÃ¡ticas (AC-MEM-01..04) y la
constituciÃ³n (Art. II.1) obliga TDD con rojo confirmado.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `scripts/`, `tests/` at repository root (ver plan.md)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: entorno de desarrollo y CI listos para importar `src/` en las pruebas

- [x] T001 Verificar que la rama `refactor/eliminar-memoria` existe y cumple `^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$` (Art. I.2). Ya creada y renombrada desde `feature/eliminar-memoria` (Art. I.3).
- [x] T002 [P] Instalar `requirements.txt` en el intÃ©rprete activo (`pip install -r requirements.txt`) y verificar con `python -c "from src.level2_agent import agent"` que no hay `ModuleNotFoundError` (research D8 â€” hoy faltan `pydantic`, `langchain*`, `langgraph`).
- [x] T003 [P] AÃ±adir el paso `pip install -r requirements.txt` a `.github/workflows/verify.yml` despuÃ©s de instalar el tooling de calidad, para que las pruebas que importan `src/` corran en CI (research D8 â€” necesario para Art. IV.1a; sin esto CI morirÃ­a con `ModuleNotFoundError` y el `skip` estÃ¡ prohibido por Art. II.7).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: dobles de prueba compartidos por todos los AC â€” SIN red real (Art. II.5)

**âš  CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Crear `tests/unit/dobles_mongo.py` con `FakeClienteMongo`, `FakeBase` y `FakeColeccion` implementando SOLO la interfaz que consume el script (`get_database`, `list_collection_names`, `get_collection`, `count_documents`, `find().sort().limit()`, `delete_many` con `.deleted_count`, `drop`) sobre una estructura `{base: {coleccion: [docs]}}` observable por las pruebas (ver data-model.md Â§4.1). Tipado estricto, docstrings, < 150 lÃ­neas.
- [x] T005 [P] Ampliar `tests/unit/conftest.py` con fixtures: (a) `agente_react_falso` que sustituye `agent._get_react_agent` con `invoke` determinista que devuelve un `AIMessage` JSON vÃ¡lido; (b) `sin_red_jira` que sustituye `agent.create_jira_ticket` por stub sin red; (c) entorno sin `MONGODB_ATLAS_CLUSTER_URI` (`monkeypatch.delenv`, `raising=False`) â€” mecanismo de rojo de AC-MEM-02 (research D7). Conservar el helper `tmp_py_file` de la spec 000.

**Checkpoint**: dobles listos â€” las pruebas del US1 pueden escribirse

---

## Phase 3: User Story 1 - AnÃ¡lisis independiente por correo (Priority: P1) ðŸŽ¯ MVP

**Goal**: cada correo se analiza solo con su evidencia; la memoria conversacional y sus colecciones dejan de existir (FR-001..FR-005)

**Independent Test**: `python -m pytest tests/unit/ -k "ac_mem" -v` en verde + `python scripts/check_trazabilidad_ac.py --spec specs/001-eliminar-memoria/spec.md` â†’ `trazabilidad_ac (4 AC cubiertos)` (quickstart V1/V4)

### FASE PRUEBAS (escribir primero, confirmar que FALLAN por la razÃ³n esperada â€” Art. II.1)

- [x] T006 [P] [US1] Crear `tests/unit/test_ac_mem_01_codigo_sin_memoria.py` con `@pytest.mark.ac("AC-MEM-01")`: (a) `src/level2_agent/memory.py` no existe; (b) bÃºsqueda en TODO `src/**/*.py` de los patrones prohibidos `get_chat_history`, `MongoDBChatMessageHistory`, `chat_history`, `session_id`, `MEMORY_TOOL`, `MEMORY_DATABASE`, `MEMORY_COLLECTION`, `add_ai_message` â†’ cero coincidencias; (c) `README.md`, `AGENTS.md` y `.env.example` sin los textos `memory.py`, `memoria conversacional`, `Chat history` (FR-004). NO escanear `docs/` (documentos fuente histÃ³ricos, research D10). Cubre AC-MEM-01, FR-001, FR-004.
- [x] T007 [P] [US1] Crear `tests/unit/test_ac_mem_02_independencia.py` con `@pytest.mark.ac("AC-MEM-02")`: construir 5 correos sintÃ©ticos (sin fixture real de terceros) asegurando â€”midendo con `genetic_logic`â€” que al menos uno cae en la banda del agente 30â€“75 y alguno en la ruta benigna (research D11); analizar los 5 en orden A y en orden B con los fixtures `agente_react_falso` y `sin_red_jira` + entorno sin `MONGODB_ATLAS_CLUSTER_URI`; para cada correo comparar `(score, es_phishing, nivel_severidad, tuple(indicadores_phishing))` entre Ã³rdenes con `assert`. Cubre AC-MEM-02, FR-002, SC-001.
- [x] T008 [P] [US1] Crear `tests/unit/test_ac_mem_03_migracion.py` con `@pytest.mark.ac("AC-MEM-03")`: tabla de decisiÃ³n del contrato (contracts/eliminar-memoria-cli.md, filas 1â€“6) contra `FakeClienteMongo`: simulaciÃ³n con docs â†’ nada borrado y exit 0; `--confirmar` con N docs â†’ colecciÃ³n eliminada y exit 0; colecciÃ³n/base ausente â†’ exit 0 sin error; `memory.py` presente â†’ exit 1 con cero escrituras. Valores lÃ­mite de `TAMANO_LOTE`: colecciones con 0, 1, `TAMANO_LOTE`, `TAMANO_LOTE + 1` y `TAMANO_LOTE * 3 + 7` documentos â†’ nÃºmero exacto de lotes borrados (`deleted_count` acumulado == N). Cubre AC-MEM-03, FR-003.
- [x] T009 [P] [US1] Crear `tests/unit/test_ac_mem_04_rag_intacto.py` con `@pytest.mark.ac("AC-MEM-04")`: base doble con `memory-agent.memory` (10 docs) y `phishguard.docs_phishing` (7 docs + Ã­ndice `vector_index`); tras ejecutar el script con `--confirmar`, `phishguard.docs_phishing` conserva SUS 7 documentos y ninguna clave de `phishguard` cambiÃ³; tambiÃ©n en modo simulaciÃ³n. Cubre AC-MEM-04, FR-005.
- [x] T010 [US1] Ejecutar `python -m pytest tests/unit/ -v` y confirmar que TODAS las pruebas de T006â€“T009 FALLAN por la razÃ³n esperada: AC-MEM-01 â†’ falla porque `memory.py` existe y hay coincidencias de patrones; AC-MEM-02 â†’ `ValueError: MONGODB_ATLAS_CLUSTER_URI no estÃ¡ configurada` (la ruta del agente aÃºn llama a `get_chat_history`); AC-MEM-03/04 â†’ `ModuleNotFoundError: scripts.eliminar_memoria`. Registrar la salida como evidencia. (Art. II.1)

### FASE IMPLEMENTACIÃ“N (cada tarea deja pruebas en verde, archivos â‰¤ 500 lÃ­neas â€” Art. III.1)

- [x] T011 [US1] Eliminar el archivo `src/level2_agent/memory.py` (FR-001). Debe desaparecer tambiÃ©n `langchain_mongodb.chat_message_histories` del cÃ³digo.
- [x] T012 [US1] Editar `src/level2_agent/agent.py`: quitar `from .memory import get_chat_history` (lÃ­nea 27), `chat_history = get_chat_history(email_data.message_id)` (lÃ­nea 205) y los bloque `chat_history.add_user_message(...)` / `chat_history.add_ai_message(...)` (lÃ­neas 228â€“231). La invocaciÃ³n queda `agent.invoke({"messages": messages})` sin estado previo (FR-001, FR-002). No tocar nada mÃ¡s del archivo.
- [x] T013 [P] [US1] Editar `src/level2_agent/models.py`: quitar las constantes `MEMORY_DATABASE = "memory-agent"` y `MEMORY_COLLECTION = "memory"` (lÃ­neas 33â€“34, FR-001). NO tocar `VECTOR_*` (FR-005).
- [x] T014 [P] [US1] Editar `src/level2_agent/prompts.py`: quitar el bloque `MEMORY_TOOL` (lÃ­neas 11â€“12) y `tools += MEMORY_TOOL` (lÃ­nea 19). No modificar el resto del prompt (research D2, fuera de alcance).
- [x] T015 [P] [US1] Actualizar documentaciÃ³n afectada (FR-004, Art. IV.1h): `README.md` â€” quitar la lÃ­nea `memory.py # Chat history en MongoDB` del Ã¡rbol (lÃ­nea 139) y cambiar el bullet "Vector store y memoria conversacional" (lÃ­nea 195) a solo "Vector store (RAG)"; `AGENTS.md` â€” quitar la menciÃ³n al namespace `memory-agent.memory` (lÃ­nea 39); verificar que `.env.example` no contiene variables de memoria (inventario D1: no debe cambiar).
- [x] T016 [US1] Implementar `scripts/eliminar_memoria.py` (FR-003) segÃºn el contrato `contracts/eliminar-memoria-cli.md`: constantes `BASE_HISTORIAL = "memory-agent"` y `TAMANO_LOTE = 1000` (Art. III.6); validaciÃ³n previa (aborta exit 1 si `src/level2_agent/memory.py` existe, si falta `MONGODB_ATLAS_CLUSTER_URI` o si la base no es la objetivo); modo simulaciÃ³n por defecto (cero escrituras); `--confirmar` activa el borrado por lotes (`find().sort("_id", 1).limit(TAMANO_LOTE)` â†’ `delete_many({_id: {$in}})` hasta vaciar) y `drop()` final por colecciÃ³n; colecciÃ³n ausente â†’ sin error; salida en espaÃ±ol por stdout, errores por stderr; funciones â‰¤ 40 lÃ­neas, `mypy --strict`, docstrings. Cubre FR-003, AC-MEM-03, AC-MEM-04.
- [x] T017 [US1] Ejecutar `python -m pytest tests/unit/ -v --cov=scripts --cov-branch` y confirmar: TODAS verdes (cero fallos, cero `skip` nuevos) y cobertura de `scripts/` â‰¥ 80 % lÃ­neas y ramas. Registrar la salida como evidencia. (Art. II.1, II.3, IV.1aâ€“b)

**Checkpoint**: US1 completa â€” el anÃ¡lisis es independiente y la memoria no existe en cÃ³digo, docs ni datos

---

## Phase 4: Polish & VerificaciÃ³n (Cross-Cutting)

**Purpose**: evidencia del Art. IV.1 y del Art. IV.3

- [x] T018 [P] Ejecutar `python scripts/verify.py` y confirmar exit 0 (8 compuertas: longitud, rama, cobertura, trazabilidad, secretos, dependencias, lint, tipos). Evidencia: salida completa. (Art. IV.1a,d,e,f,g)
- [x] T019 [P] Ejecutar `python scripts/check_trazabilidad_ac.py --spec specs/001-eliminar-memoria/spec.md` y confirmar `trazabilidad_ac (4 AC cubiertos)` â€” AC-MEM-01..04 con su prueba marcada y verde. (Art. II.6)
- [x] T020 [P] Verificar `python -m ruff check scripts/ tests/unit/` y `python -m mypy scripts/ tests/unit/` sin errores; y ningÃºn `.py` de `scripts/` ni `tests/unit/` por encima de 500 lÃ­neas. (Art. III.1, III.8)
- [x] T021 [P] Ejecutar las validaciones de `quickstart.md` (V1â€“V7) y registrar resultados; la V5 manual contra Atlas real queda como `[VERIFICAR]` si no se ejecuta (research D11 â€” Art. VI.3). (Art. IV.1h,i)
- [x] T022 Generar el informe final del Art. IV.3: comando ejecutado y resultado de las pruebas, % de cobertura (lÃ­neas y ramas), lista de AC-MEM-01..04 con su prueba, y desviaciones respecto a la spec (incluida la validaciÃ³n manual de V5 si no se ejecutÃ³).
- [x] T023 Commitear en `refactor/eliminar-memoria` con Conventional Commits mencionando los CA, p. ej. `refactor: eliminar memoria conversacional del agente (AC-MEM-01..04)`, en grupos lÃ³gicos (pruebas / eliminaciÃ³n / script / docs). NO hacer commit en `main` (Art. I.4â€“I.5).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies â€” can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T002 para importar `src/`) â€” BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (dobles T004â€“T005)
  - FASE PRUEBAS (T006â€“T009) â†’ rojo (T010) â†’ FASE IMPLEMENTACIÃ“N (T011â€“T016) â†’ verde (T017)
- **Polish (Phase 4)**: Depends on US1 completa (T017)

### User Story Dependencies

- **User Story 1 (P1)**: Ãºnica user story; puede empezar tras Phase 2, sin dependencias de otras historias. MVP de la spec completa.

### Within Each User Story

- Tests escritos y en FALLA antes de cualquier implementaciÃ³n (Art. II.1)
- EliminaciÃ³n de `src/` (T011â€“T014) y docs (T015) antes que el script (T016) no es obligatorio entre sÃ­ â€” son archivos independientes â€” pero el verde completo (T017) exige los 6
- VerificaciÃ³n solo despuÃ©s del verde

### Parallel Opportunities

- Setup: T002 âˆ¥ T003
- Foundational: T004 âˆ¥ T005
- Pruebas US1: T006 âˆ¥ T007 âˆ¥ T008 âˆ¥ T009 (archivos distintos)
- ImplementaciÃ³n US1: T013 âˆ¥ T014 âˆ¥ T015 (archivos distintos); T011+T012 van juntos (mismo mÃ³dulo `agent.py`/borrado de `memory.py`, se hacen en un solo paso lÃ³gico)
- Polish: T018 âˆ¥ T019 âˆ¥ T020 âˆ¥ T021 (solo lectura)

## Parallel Example: User Story 1

```text
# FASE PRUEBAS (4 archivos en paralelo):
Task: "test_ac_mem_01_codigo_sin_memoria.py con @pytest.mark.ac(\"AC-MEM-01\")"
Task: "test_ac_mem_02_independencia.py con @pytest.mark.ac(\"AC-MEM-02\")"
Task: "test_ac_mem_03_migracion.py con @pytest.mark.ac(\"AC-MEM-03\")"
Task: "test_ac_mem_04_rag_intacto.py con @pytest.mark.ac(\"AC-MEM-04\")"

# FASE IMPLEMENTACIÃ“N (3 archivos en paralelo):
Task: "quitar MEMORY_* de src/level2_agent/models.py"
Task: "quitar MEMORY_TOOL de src/level2_agent/prompts.py"
Task: "actualizar README.md y AGENTS.md (FR-004)"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks stories)
3. Complete Phase 3: User Story 1 (pruebas â†’ rojo â†’ implementaciÃ³n â†’ verde)
4. **STOP and VALIDATE**: quickstart V1/V4 + trazabilidad 4/4
5. Phase 4: evidencia del Art. IV.1 y commit

### Incremental Delivery

1. Setup + Foundational â†’ dobles y CI listos
2. US1 â†’ la spec entera es un Ãºnico incremento: cÃ³digo sin memoria + script de migraciÃ³n + docs (no hay incrementos parciales de valor porque FR-001..005 son interdependientes: un repo con el mÃ³dulo eliminado pero sin el script de migraciÃ³n incumplirÃ­a AC-MEM-03)
3. Polish â†’ evidencia y merge-ready

## Notes

- **`[P]` en una tarea** = archivos distintos, sin dependencias (ejemplo de paralelismo, no es una tarea)
- **`[US1]` en una tarea** = trazabilidad a la user story que la origina
- Verify tests fail before implementing (T010 es obligatorio: sin rojo no se implementa)
- Commit after each task or logical group (T023)
- NO usar `skip`/`xfail` ni bajar umbrales para que la spec pase (Art. II.7)
- NO tocar `requirements.txt`, `pyproject.toml`, `tests/test_pipeline.py`, `tests/fixtures/` ni el RAG (FR-005, Art. VI.1)

---

## VerificaciÃ³n de cumplimiento de la constituciÃ³n (Art. VII.3)

| ArtÃ­culo | CÃ³mo lo garantizan las tareas |
|---|---|
| I.1â€“I.5 | T001 (rama y regex), T023 (commits convencionales con CA, sin main) |
| II.1 | T006â€“T010 (pruebas primero con rojo obligatorio), T017 (verde) |
| II.2 | 5 tÃ©cnicas justificadas en research D7: particiÃ³n (T006, T007), valores lÃ­mite (T008: `TAMANO_LOTE` Â± 1), tabla de decisiÃ³n (T008: filas 1â€“6 del contrato), dobles (T004â€“T005, T008â€“T009), regresiÃ³n (T007) |
| II.3 | T017 (â‰¥ 80 % lÃ­neas y ramas sobre `scripts/`; sin tocar umbrales, research D9) |
| II.4 | Cada prueba de T006â€“T009 tiene aserciones observables (borrados, igualdad de resultados, cero coincidencias) |
| II.5 | T004â€“T005 (dobles; sin Atlas ni red en pruebas) |
| II.6 | T006â€“T009 con `@pytest.mark.ac("AC-MEM-01..04")`, verificado en T019 |
| II.7 | Notes: prohibido skip/bajar umbrales; T010 exige rojo real |
| III.1â€“III.9 | T016 (â‰¤ 40 lÃ­neas por funciÃ³n, constantes con nombre, docstrings, errores explÃ­citos), T020 (â‰¤ 500, ruff, mypy strict) |
| IV.1aâ€“i | T017â€“T021 con evidencia de comandos; T022 informe |
| V.2 | T016 (simulaciÃ³n por defecto, `--confirmar` explÃ­cito) |
| V.3â€“V.4 | T016 (solo lee `MONGODB_ATLAS_CLUSTER_URI` de entorno; logs sin contenido de correos ni secretos) |
| VI.1â€“VI.3 | Notes (alcance cerrado); T021 marca `[VERIFICAR]` lo no ejecutado |
| VII.3 | Esta secciÃ³n |

