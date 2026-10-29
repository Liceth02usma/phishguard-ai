# Tasks: Scoring con Clasificador Lineal y Banderas (spec 007)

**Input**: Design documents from `/specs/007-scoring-genetico/`

**Prerequisites**: plan.md ✓, spec.md ✓ (1 user story, P1), research.md (D1–D13) ✓, data-model.md ✓, contracts/calcular-score-final.md ✓, quickstart.md ✓

**Tests**: **Sí** — constitución Art. II.1 exige TDD rojo→verde. Cada prueba lleva `@pytest.mark.ac("AC-SCO-NN")`.

**Organization**: una única user story (US1). La fase fundacional (entrenamiento + loader del modelo) la desbloquea.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos)
- **[Story]**: US1 (única historia)

## Phase 1: Setup (infraestructura compartida)

- [ ] T001 [P] Agregar override `mypy --strict` en `pyproject.toml` para `["src.level3_logic.scoring", "src.level3_logic.scoring.*", "src.level3_logic.modelo"]` (aditivo)
- [ ] T002 [P] Ampliar `scripts/verify.py`: añadir `--cov=src/level3_logic/scoring`, `--cov=src/level3_logic/modelo` y `--cov=src/level3_logic/genetic_logic` a la lista de pytest, y `"src/level3_logic/scoring"`, `"src/level3_logic/modelo.py"` a `RUTAS_CALIDAD_SRC` (ruff NO incluye `genetic_logic.py`: solo modificación funcional, research D8)
- [ ] T003 [P] Añadir a `.env.example` la variable `DOMINIOS_PROVEEDORES_CONFIANZA=` con comentario en español y `RUTA_MODELO=` con comentario

## Phase 2: Foundational (bloquea US1)

> El modelo pre-entrenado y su loader son prerequisite de toda puntuación.

- [ ] T004 Crear `scripts/entrenar_clasificador.py`: lee `data/evaluacion/fuente_entrenamiento/100correos.csv` (32 columnas de genes + `label`), entrena `LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, random_state=42)` con scikit-learn, verifica que `score(genes=0) < 30` (AC-SCO-01, research D13), exporta `data/modelo/clasificador_v1.json` con `version="clasificador_v1"`, `fecha`, `conjunto_entrenamiento`, `hiperparametros`, `metricas_entrenamiento` (accuracy, recall, f1), `intercepto` y `coeficientes` (32 claves de `MAPEO_INDICES`); ejecutar el script y confirmar que el JSON se creó y AC-SCO-01 se cumple
- [ ] T005 [P] Escribir **rojo** `tests/unit/test_modelo.py`: carga del JSON real (32 claves exactas de `MAPEO_INDICES`, `"version" == "clasificador_v1"`, `intercepto` es float, `coeficientes` tiene 32 entradas), rechazo de JSON faltente/ilegible/schema inválido con `ModeloError` (Art. III.9), cache de proceso (segunda lectura no relee disco), validador de claves de más y de menos — marcar `@pytest.mark.ac("AC-SCO-03")` solo la aserción de versión
- [ ] T006 Implementar `src/level3_logic/modelo.py`: modelo Pydantic `ClasificadorLineal` (campos y validaciones del data-model.md: `coeficientes` con **exactamente** las 32 claves de `MAPEO_INDICES` vía `model_validator`, faltantes/sobrantes ⇒ error), `ModeloError(ScoringError)` y `cargar_modelo(ruta: Path | None = None) -> ClasificadorLineal` con cache de proceso y default `data/modelo/clasificador_v1.json`, más `predecir_probabilidad(modelo, genes) -> float` (producto punto + sigmoide en Python puro) — ejecutar `python -m pytest tests/unit/test_modelo.py -q` hasta verde

## Phase 3: User Story 1 — Score final que combina clasificador lineal + banderas (P1)

**Goal**: `score_final = min(100, score_clasificador + min(60, puntos_banderas))` reproducible, con modelo versionado y corrección de defectos M10 (FR-001..FR-007).

**Independent Test Criteria**: un correo con genes y banderas conocidos produce el `score_final` esperado con `version_modelo` guardado; monotonicidad; límites 59/60/61 y 99/100/101; "urgente" ⊄ "insurgente".

### 3.1 Pruebas rojas (todas [P], archivos distintos)

- [ ] T007 [P] [US1] Escribir `tests/unit/test_ac_sco_01_score_bajo.py`: correo limpio (0 genes) ⇒ `score_clasificador < 30` usando `evaluate` con modelo real (intercepto del clasificador_v1) y la sigmoide directa con `genes=0`; `@pytest.mark.ac("AC-SCO-01")`
- [ ] T008 [P] [US1] Escribir `tests/unit/test_ac_sco_06_palabra_completa.py`: "urgente" NO coincide en "insurgente", sí con puntuación pegada ("urgente,"), mayúsculas y acentos; probar helper y gen léxico end-to-end; `@pytest.mark.ac("AC-SCO-06")`
- [ ] T009 [P] [US1] Escribir `tests/unit/test_genetico_genes.py`: matriz por partición de equivalencia que active los 32 genes por grupos verificando `genes_implicados`, incluida FR-005: genes 0 y 28 **no** se activan cuando dominios están en listas (inyectar `ConfigScoring` de prueba) y sí con dominios desconocidos — aporta cobertura de `genetic_logic.py` (Art. II.3)
- [ ] T010 [P] [US1] Escribir `tests/unit/test_ac_sco_02_monotonicidad.py` con `hypothesis`: para coeficientes arbitrarios (32 bits) y puntos de banderas crecientes, `score_final` nunca baja al agregar una bandera; `@pytest.mark.ac("AC-SCO-02")`
- [ ] T011 [P] [US1] Escribir `tests/unit/test_ac_sco_05_limites.py` como **tabla de valores límite**: puntos 59/60/61 ⇒ tope 60; score_final 99/100/101 previo a `min(100,…)` ⇒ 99/100/100; `@pytest.mark.ac("AC-SCO-05")`
- [ ] T012 [P] [US1] Escribir `tests/unit/test_ac_sco_03_version.py`: `ScoreFinal.version_modelo == "clasificador_v1"` derivado del JSON (no de constante), y que el reporte incluye `version_modelo` y `score_clasificador`; `@pytest.mark.ac("AC-SCO-03")`
- [ ] T013 [P] [US1] Escribir `tests/unit/test_scoring_motor.py`: `calcular_score_final` con **dobles inyectados** de 003/004/005 (`DependenciasScoring` con `cliente_rdap` nulo, `deps_urls` fake, `ahora` fijo): suma de tres catálogos con tope 60, `origen` correcto en `BanderaScoring`, adjuntos por parámetro (D7), cero banderas ⇒ `puntos_banderas == 0`, degradación sin red, invariante del `model_validator` de `ScoreFinal` y errores de `ConfigScoring` inválida — **cero red real** (Art. II.5)
- [ ] T014 [US1] Ejecutar `python -m pytest tests/unit/ -k "sco or modelo or genetico" -q` y confirmar el **rojo** por la razón esperada (`ModuleNotFoundError` de `src.level3_logic.scoring` / `modelo` y aserciones de genético sin modelo) — adjuntar salida en el commit (Art. II.1)

### 3.2 Implementación (verde)

- [ ] T015 [US1] En `src/level3_logic/genetic_logic.py`: añadir `contiene_palabra_completa(palabra: str, texto: str) -> bool` (regex compilada `(?<!\w)…(?!\w)` con `re.escape` e `re.IGNORECASE`, research D4) y usarla en `_contiene_alguna` y detectores de keywords de URL (FR-004)
- [ ] T016 [US1] En `src/level3_logic/genetic_logic.py`: añadir `ConfigGenetico(modelo: ClasificadorLineal, dominios_propios: tuple[str,...] = (), proveedores_confianza: tuple[str,...] = ())` y parámetro keyword `config: ConfigGenetico | None = None` en `evaluate` (default: `cargar_modelo()` + env); aplicar **FR-001** (scoring con coeficientes del modelo: `score = 100 * σ(Σ modelo.coeficientes[gene] * gene + modelo.intercepto)`), **FR-005** (genes 0 y 28 condicionados a listas) y **FR-006** (retornar también `version_modelo = modelo.version`; eliminar `PESOS_AG` hardcodeado y `VERSION_PESOS` constante — la fuente es el JSON; `MAPEO_INDICES` permanece); conservar shape legacy (`score`, `genes_implicados`, `suma_lineal_ag`) y docstring en español; archivo < 450 líneas (Art. III.1)
- [ ] T017 [P] [US1] Crear `src/level3_logic/scoring/modelos.py`: `ScoringError`, `ModeloError`, `BanderaScoring` (`origen: Literal["cabeceras","urls","adjuntos"]`, `codigo`, `puntos ge=0`) y `ScoreFinal` con validaciones del data-model.md (`score_final int ge=0 le=100`, `puntos_banderas le=TOPE_PUNTOS_BANDERAS` **importado** de `src.level2_agent.banderas.modelos`, `version_modelo min_length=1`, invariante `score_final == min(100, round(score_clasificador + puntos_banderas))` por `model_validator`)
- [ ] T018 [P] [US1] Crear `src/level3_logic/scoring/configuracion.py`: `ConfigScoring` (`dominios_propios`, `proveedores_confianza`, `ruta_modelo`) + constante `PROVEEDORES_CONFIANZA_POR_DEFECTO` (lista D5) + `desde_entorno()` leyendo `DOMINIOS_PROPIOS`, `DOMINIOS_PROVEEDORES_CONFIANZA` y `RUTA_MODELO` (coma-separadas; env malformada ⇒ `ScoringError`)
- [ ] T019 [US1] Crear `src/level3_logic/scoring/motor.py`: `DependenciasScoring` (dataclass frozen: `cliente_rdap`, `deps_urls`, `ahora` — defaults de producción) y `calcular_score_final(email_data, config=None, deps=None, adjuntos_analizados=()) -> ScoreFinal` con el orden de 8 pasos del contrato (§3): `cargar_modelo` → `evaluate` → `evaluar_banderas` → `analizar_urls` → suma adjuntos → `min(60, …)` → `min(100, round(…))` → `BanderaScoring` agregados; funciones ≤ 40 líneas (Art. III.2); docstring en español
- [ ] T020 [US1] Crear `src/level3_logic/scoring/__init__.py` exponiendo la superficie del contrato (§1): `calcular_score_final`, `ScoreFinal`, `BanderaScoring`, `ConfigScoring`, `DependenciasScoring`, `ScoringError`, `ModeloError`
- [ ] T021 [US1] Cablear en `src/level2_agent/agent.py`: reemplazar cuerpo de `_genetic_score` por `calcular_score_final(email_data)` (manteniendo fallback `SCORE_FALLBACK=50.0` + `version_modelo="indeterminada"` + log en excepción), usar `score_final` para branch 30/75 (umbrales **sin cambiar**), añadir a `PhishingReport` los campos `score_clasificador: float` y `version_modelo: str` poblados en reportes (máx. 5 parámetros, Art. III.2; sin tocar prompts ni veredictos)
- [ ] T022 [US1] Ejecutar `python -m pytest tests/unit/ -q` y llevar toda la suite a verde (incluidas pruebas de 003/004/005, que **no deben** verse afectadas)
- [ ] T023 [US1] Verificar cobertura: `python -m pytest tests/unit/ --cov=src/level3_logic/scoring --cov=src/level3_logic/modelo --cov=src/level3_logic/genetic_logic --cov-branch --cov-fail-under=80 -q` ⇒ ≥ 80 % líneas y ramas en los tres (Art. II.3); si `genetic_logic.py` queda corto, ampliar la matriz de T009 (nunca bajar umbral, Art. II.7)

## Phase 4: Polish & cross-cutting concerns

- [ ] T024 [P] Ejecutar `python scripts/verify.py` completo en la rama y dejar EXIT=0
- [ ] T025 [P] Ejecutar `python scripts/check_trazabilidad_ac.py --spec specs/007-scoring-genetico/spec.md` ⇒ AC-SCO-01..06 todos cubiertos, exit 0
- [ ] T026 [P] Actualizar `README.md` (aditivo): entrada del árbol para `src/level3_logic/scoring/`, `modelo.py` y `scripts/entrenar_clasificador.py`, mención de `data/modelo/clasificador_v1.json`
- [ ] T027 Actualizar `AGENTS.md`: **reemplazar** la nota "Genetic weights are hardcoded…" por la nueva realidad (modelo cargado de `data/modelo/clasificador_v1.json` vía `cargar_modelo()`; `MAPEO_INDICES` sigue en código; scoring con coeficientes entrenados) y añadir nota del módulo `scoring/` (fachada `calcular_score_final`, tope 60 importado de 003, env vars, script de entrenamiento); borrar `data/pesos/` si existe (obsoleto)
- [ ] T028 Validar pipeline legado vivo (requiere `GOOGLE_API_KEY`): `python tests/test_pipeline.py`; medir rutas de las 3 fixtures con scoring nuevo; si `ai_agent` (0 genes) deja de caer en 30–75, **pedir aprobación explícita al usuario** antes de actualizar metadata `_test` (motivo: AC-SCO-01; research D10); **no ejecutar si no hay aprobación** (Art. II.7)
- [ ] T029 AC-SCO-04 + FR-007 (report-only): cuando la rama `test/conjunto-evaluacion` (spec 015) conviva, ejecutar `python scripts/evaluar_desempeno.py --modo grabado` y registrar recall/FP reales (si no cumplen, **no** ajustar); correlacionar los 32 genes del CSV contra `label` y documentar coeficientes contradictorios — resultados en `specs/007-scoring-genetico/informe-implantacion.md`
- [ ] T030 Escribir informe final `specs/007-scoring-genetico/informe-implantacion.md` (Art. IV.3): comando y resultado de pruebas, cobertura, lista AC → prueba, desviaciones

## Dependencies

- **Setup (T001–T003)**: sin dependencias; en paralelo.
- **Fundacional (T004→T005→T006)**: T004 (entrenamiento + JSON) es prerequisite de todo; T005 (rojas) antes que T006 (implementación). T006 desbloquea T016 y T019.
- **US1 rojas (T007–T013)**: en paralelo entre sí; todas anteriores a T014 y a la implementación.
- **Implementación**: T015 → T016 (coincidencia antes de config); T017 → T019; T018 → T019; T020 al final; T021 después de T019/T020; T022/T023 al cierre.
- **Polish (T024–T030)**: T024–T027 en paralelo; T028 requiere aprobación; T029 requiere rama 015; T030 cierra.

## Parallel Execution Examples

- **Grupo Setup**: `T001 + T002 + T003` — tres archivos distintos.
- **Grupo rojas US1**: `T007 + T008 + T009 + T010 + T011 + T012 + T013` — siete archivos independientes.
- **Grupo implementación paquete**: `T017 + T018`( T018` en paralelo; T019 los consume.
- **Grupo polish**: `T024 + T025 + T026 + T027` — compuertas y docs aditivas.

## Implementation Strategy

**MVP = US1 completa** (única historia). Orden: Setup → fundacional (entrenar modelo + loader) → rojas US1 → genético corregido → paquete scoring → wire → verde/cobertura → polish. El script de entrenamiento (T004) es el primer paso fundacional — sin el JSON del modelo, nada del scoring funciona. Riesgos: (1) el entrenamiento puede no satisfacer AC-SCO-01 → ajustar `class_weight` o `C` (D13); (2) carrera por directorio compartido — commitear pronto; (3) T028 depende de aprobación humana y T029 de la rama 015 — ninguno bloquea el merge del resto.
