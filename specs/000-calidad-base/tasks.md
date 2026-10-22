---
description: "Task list for feature implementation"
---

# Tasks: Compuertas de Calidad AutomÃ¡ticas

**Input**: Design documents from `/specs/000-calidad-base/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/verify-cli.md, quickstart.md

**Tests**: INCLUIDOS â€” la constituciÃ³n (Art. II.1) exige pruebas primero, derivadas de los AC, confirmadas en rojo antes de implementar.

**Organization**: Una user story (P1) con 6 AC (AC-CAL-01..06). Fase pruebas â†’ fase implementaciÃ³n â†’ fase verificaciÃ³n.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (distintos archivos, sin dependencias)
- **[Story]**: user story (US1)
- Cada tarea referencia el AC que cubre y la ruta exacta del archivo.

## Path Conventions

- Scripts de calidad: `scripts/`
- Pruebas: `tests/unit/`
- Config: raÃ­z del repo (`pyproject.toml`, `.gitignore`, `.env.example`, `.pre-commit-config.yaml`, `Makefile`)
- CI: `.github/workflows/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Config del proyecto y estructura base. Sin lÃ³gica de compuertas todavÃ­a.

- [x] T001 Verificar que la rama `chore/calidad-base` existe y cumple `^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$` (Art. I.2). Ya creada en commit `160d8dd`.
- [x] T002 Crear `pyproject.toml` con: `[tool.pytest.ini_options]` marker `ac(id)` (Art. II.6), `testpaths=["tests"]`, `[tool.coverage.run] branch=true source=["scripts"]`, `[tool.ruff]` (line-length 100, reglas E,F,W,I,UP,B,SIM), `[tool.mypy] strict=true`, `[project]` dependencias de dev con versiÃ³n fija (`pytest`, `pytest-cov`, `ruff`, `mypy`, `pip-audit`).
- [x] T003 [P] Crear `.env.example` sin valores reales (variables `GOOGLE_API_KEY=`, `MONGODB_ATLAS_CLUSTER_URI=`, `VT_API_KEY=`, `JIRA_INSTANCE_URL=`, `JIRA_USER_EMAIL=`, `JIRA_API_TOKEN=`, `DRY_RUN=true`). Ver `contracts/verify-cli.md`.
- [x] T004 [P] Ampliar `.gitignore` con: `.env`, `credenciales.json`, `token.json`, `.coverage`, `.coverage.*`, `htmlcov/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`. (Art. V.3, RF7)
- [x] T005 [P] Crear `.pre-commit-config.yaml` con hooks: `ruff check`, `ruff format`, `mypy`, `gitleaks`. (RF6)
- [x] T006 [P] Crear `Makefile` con target `verify: ; python scripts/verify.py` (wrapper Unix, decisiÃ³n D1). (RF1)
- [x] T007 [P] Crear `.github/workflows/verify.yml` que en cada PR ejecute `pip install -r requirements.txt && pip install pytest pytest-cov ruff mypy pip-audit && python scripts/verify.py`. (RF6, AC-CAL-06)

**Checkpoint**: config lista. Falta `scripts/verify.py` (se crea en implementaciÃ³n); el workflow referenciarÃ¡ un script que aÃºn no existe â€” es esperado hasta Phase 3.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Constantes y conftest compartidos que tanto pruebas como implementaciÃ³n importan. DEBE completarse antes de cualquier tarea de US1.

- [x] T008 Crear `scripts/_comunes.py` con constantes `LIMITE_LINEAS = 500`, `COBERTURA_MIN = 80`, `RAMA_REGEX = r"^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$"`, `RAMAS_EXENTAS = {"main", "develop"}` y dataclasses `Compuerta`, `ResultadoCompuerta`, `ResultadoVerify` (ver `data-model.md`). â‰¤500 lÃ­neas, tipado, docstrings. (Art. III.6 â€” sin nÃºmeros mÃ¡gicos)
- [x] T009 Crear `tests/unit/conftest.py` que registre el marker `ac` y exponga un helper `tmp_py_file(lineas)` para generar archivos `.py` temporales en pruebas. (Art. II.6)

**Checkpoint**: fundaciÃ³n lista. Las pruebas de US1 pueden importar `_comunes` y usar el marker `ac`.

---

## Phase 3: User Story 1 - Compuertas de calidad ejecutables con un solo comando (Priority: P1) â€” MVP

**Goal**: Un comando `python scripts/verify.py` ejecuta 8 compuertas y falla si alguna obligatoria se incumple, listando el motivo.

**Independent Test**: ejecutar `python scripts/verify.py` contra un repo que viola cada regla y verificar que falla con el mensaje esperado; contra un repo limpio, exit 0.

### FASE PRUEBAS (escribir primero, confirmar que FALLAN por la razÃ³n esperada â€” Art. II.1)

> Las pruebas importan mÃ³dulos de `scripts/` que aÃºn no existen â†’ ImportError (rojo esperado).

- [x] T010 [P] [US1] Crear `tests/unit/test_check_longitud_archivos.py` con `@pytest.mark.ac("AC-CAL-01")`: prueba que un archivo de 500 lÃ­neas pasa y uno de 501 falla (valores lÃ­mite, en tmp dir). Cubre AC-CAL-01.
- [x] T011 [P] [US1] Crear `tests/unit/test_check_nombre_rama.py` con `@pytest.mark.ac("AC-CAL-02")`: tabla de decisiÃ³n â€” `feature/analisis-urls`, `fix/x`, `chore/a-b-c` pasan; `Feature/x`, `feature/Analisis`, `001-analisis`, `feature/`, `feature/a_b` fallan; `main` y `develop` exentas. FunciÃ³n pura sobre el string. Cubre AC-CAL-02.
- [x] T012 [P] [US1] Crear `tests/unit/test_check_trazabilidad_ac.py` con `@pytest.mark.ac("AC-CAL-05")`: dado una spec con AC-CAL-01..06 y un conjunto de pruebas marcadas, un AC sin prueba aparece en el informe. Cubre AC-CAL-05.
- [x] T013 [P] [US1] Crear `tests/unit/test_verify_cobertura.py` con `@pytest.mark.ac("AC-CAL-03")`: un mÃ³dulo sintÃ©tico con cobertura de ramas 78 % hace fallar la compuerta de cobertura (umbral 80). Cubre AC-CAL-03.
- [x] T014 [P] [US1] Crear `tests/unit/test_verify_secretos.py` con `@pytest.mark.ac("AC-CAL-04")`: una cadena con forma de API key (ej. `AKIA[0-9A-Z]{16}`) en un tmp dir es detectada por gitleaks; si gitleaks no estÃ¡ instalado, `pytest.skip` (no `xfail`). Cubre AC-CAL-04.
- [x] T015 [P] [US1] Crear `tests/unit/test_verify_orquestador.py` con `@pytest.mark.ac("AC-CAL-01")` parcial: el orquestador `verify.py` ejecuta todas las compuertas, agrega resultados, y exit 1 si alguna obligatoria falla / 0 si todas pasan (con dobles de las compuertas). Cubre el comportamiento agregado de RF1.
- [x] T016 [US1] Ejecutar `pytest tests/unit/ -v` y confirmar que TODAS las pruebas de T010â€“T015 fallan por la razÃ³n esperada (ImportError o AssertionError). Registrar la salida como evidencia. (Art. II.1)

### FASE IMPLEMENTACIÃ“N (cada tarea deja pruebas en verde, archivos â‰¤500 lÃ­neas â€” Art. III.1)

- [x] T017 [P] [US1] Implementar `scripts/check_longitud_archivos.py`: recorre `src/` y `tests/` contando lÃ­neas de `.py`, falla si alguno > `LIMITE_LINEAS` (500), lista infractores con conteo. FunciÃ³n pura `evaluar_longitud(paths) -> ResultadoCompuerta`. Cubre RF2, AC-CAL-01.
- [x] T018 [P] [US1] Implementar `scripts/check_nombre_rama.py`: funciÃ³n pura `evaluar_nombre_rama(rama: str) -> ResultadoCompuerta` que aplica `RAMA_REGEX` y exime `RAMAS_EXENTAS`. El CLI lee `git branch --show-current`. Cubre RF3, AC-CAL-02.
- [x] T019 [P] [US1] Implementar `scripts/check_trazabilidad_ac.py`: parsea la spec de la rama (regex `AC-[A-Z]+-\d+`), recolecta pruebas marcadas `@pytest.mark.ac(...)` via `pytest --collect-only -q`, y emite la lista de AC sin prueba. Exit 0 si todos cubiertos, 1 si falta. Cubre RF4, AC-CAL-05.
- [x] T020 [US1] Implementar `scripts/verify.py` orquestador: ejecuta en orden las 8 compuertas (`longitud_archivos`, `nombre_rama`, `cobertura` via `pytest --cov --cov-branch --cov-fail-under=80`, `trazabilidad_ac`, `secretos` via `gitleaks`, `dependencias` via `pip-audit`, `lint` via `ruff check`, `tipos` via `mypy --strict`), agrega `ResultadoCompuerta`, imprime `[PASS]`/`[FAIL]` por compuerta, exit 0/1. Flags `--solo <compuerta>`, `--no-cobertura`. â‰¤500 lÃ­neas. Cubre RF1, AC-CAL-03, AC-CAL-04.
- [x] T021 [US1] Ejecutar `pytest tests/unit/ -v --cov=scripts --cov-branch` y confirmar que TODAS las pruebas de T010â€“T015 pasan (verde) y cobertura de `scripts/` â‰¥80 % lÃ­neas y ramas. Registrar la salida como evidencia. (Art. II.3)

**Checkpoint**: `python scripts/verify.py` funciona end-to-end. Las 8 compuertas se ejecutan y el exit code refleja el resultado.

---

## Phase 4: Polish & VerificaciÃ³n (Cross-Cutting)

**Purpose**: ValidaciÃ³n final contra la constituciÃ³n (Art. IV) y actualizaciÃ³n de docs.

- [x] T022 [P] Ejecutar `python scripts/verify.py` y confirmar exit 0 (repo limpio tras esta spec). Evidencia: salida completa. (AC-CAL-06 local)
- [x] T023 [P] Ejecutar `python scripts/check_trazabilidad_ac.py --spec specs/000-calidad-base/spec.md` y confirmar que los 6 AC-CAL-01..06 tienen prueba marcada y verde. (Art. II.6, AC-CAL-05)
- [x] T024 [P] Verificar `ruff check scripts/ tests/` y `mypy --strict scripts/` sin errores. (Art. III.8)
- [x] T025 [P] Verificar que ningÃºn archivo de `scripts/` o `tests/` supera 500 lÃ­neas. (Art. III.1)
- [x] T026 Actualizar `README.md` con secciÃ³n "Comando de calidad" documentando `python scripts/verify.py` y el marker `ac`. (Art. IV.1h)
- [x] T027 [P] Ejecutar las validaciones de `quickstart.md` (Validaciones 1â€“6) y registrar resultados. (Art. IV.1i)
- [x] T028 Generar el informe final del Art. IV.3: comando ejecutado y resultado de pruebas, % cobertura (lÃ­neas y ramas), lista de AC-CAL-01..06 con su prueba, desviaciones respecto a la spec.

**Checkpoint**: spec convergida segÃºn Art. IV. Solo entonces se declara "Converged".

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T002 debe existir antes de T016 (pytest config).
- **Foundational (Phase 2)**: depende de T002 (pyproject.toml). BLOQUEA Phase 3.
- **User Story 1 (Phase 3)**: depende de Phase 2. FASE PRUEBAS (T010â€“T016) antes de FASE IMPLEMENTACIÃ“N (T017â€“T021). T016 bloquea T017.
- **Polish (Phase 4)**: depende de Phase 3 completo.

### Within User Story 1

- T010â€“T015 (pruebas) son paralelizables [P] â€” distintos archivos.
- T016 (ejecutar pruebas, confirmar rojo) depende de T010â€“T015.
- T017â€“T019 (scripts individuales) paralelizables [P]; T020 (orquestador) depende de T017â€“T019.
- T021 (verde + cobertura) depende de T020.

### Parallel Opportunities

- T003â€“T007 (config files) en paralelo.
- T010â€“T015 (pruebas) en paralelo.
- T017â€“T019 (scripts individuales) en paralelo.
- T022â€“T025, T027 (verificaciÃ³n) en paralelo.

---

## Parallel Example: User Story 1

```bash
# FASE PRUEBAS â€” lanzar todas juntas (distintos archivos):
Task: "T010 test_check_longitud_archivos.py (AC-CAL-01)"
Task: "T011 test_check_nombre_rama.py (AC-CAL-02)"
Task: "T012 test_check_trazabilidad_ac.py (AC-CAL-05)"
Task: "T013 test_verify_cobertura.py (AC-CAL-03)"
Task: "T014 test_verify_secretos.py (AC-CAL-04)"
Task: "T015 test_verify_orquestador.py (AC-CAL-01 parcial)"

# Luego confirmar rojo (T016), luego implementaciÃ³n:
Task: "T017 check_longitud_archivos.py"
Task: "T018 check_nombre_rama.py"
Task: "T019 check_trazabilidad_ac.py"
# T020 orquestador depende de T017-T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (T001â€“T007)
2. Phase 2: Foundational (T008â€“T009)
3. Phase 3 FASE PRUEBAS (T010â€“T016) â€” confirmar rojo
4. Phase 3 FASE IMPLEMENTACIÃ“N (T017â€“T021) â€” verde + cobertura
5. **STOP and VALIDATE**: `python scripts/verify.py` exit 0
6. Phase 4: Polish & VerificaciÃ³n (T022â€“T028) â€” informe Art. IV.3

### Incremental Delivery

Esta spec es un solo incremento (MVP = US1). No hay P2/P3. La entrega es binaria: las compuertas existen y pasan, o no.

---

## Notes

- [P] = distintos archivos, sin dependencias.
- [US1] = todas las tareas de Phase 3 pertenecen a la user story 1.
- Cada AC-CAL-01..06 tiene al menos una prueba marcada (Art. II.6).
- Ninguna tarea borra/relaja pruebas o baja umbrales (Art. II.7).
- Los archivos de prueba (501 lÃ­neas, API key) se generan en tmp dirs, nunca se commitean (Art. 0.5).
- Commit despuÃ©s de cada tarea o grupo lÃ³gico, formato Conventional Commits (Art. I.5).

