# Tasks: Scoring Genético con Banderas (spec 007)

**Input**: Design documents from `/specs/007-scoring-genetico/`

**Prerequisites**: plan.md ✓, spec.md ✓ (1 user story, P1), research.md (D1–D10) ✓, data-model.md ✓, contracts/calcular-score-final.md ✓, quickstart.md ✓

**Tests**: **Sí se generan** — la constitución (Art. II.1) exige TDD rojo→verde y el hint de la spec pide `hypothesis` + tabla de valores límite. Cada prueba lleva `@pytest.mark.ac("AC-SCO-NN")` donde aplique (Art. II.6).

**Organization**: una única user story (US1). La fase fundacional (pesos versionados) la desbloquea; el resto de tareas de US1 son ejecutables en paralelo tras ella.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias de tareas incompletas)
- **[Story]**: US1 (única historia de la spec)

## Phase 1: Setup (infraestructura compartida)

- [ ] T001 [P] Agregar override `mypy --strict` en `pyproject.toml` para `["src.level3_logic.scoring", "src.level3_logic.scoring.*", "src.level3_logic.pesos"]` (aditivo, junto a los overrides de banderas/analisis_urls)
- [ ] T002 [P] Ampliar `scripts/verify.py`: añadir `--cov=src/level3_logic/scoring`, `--cov=src/level3_logic/pesos` y `--cov=src/level3_logic/genetic_logic` a la lista de pytest, y `"src/level3_logic/scoring"`, `"src/level3_logic/pesos.py"` a `RUTAS_CALIDAD_SRC` (ruff NO incluye `genetic_logic.py`: solo se modifica funcionalmente, research D8)
- [ ] T003 [P] Añadir a `.env.example` la variable nueva `DOMINIOS_PROVEEDORES_CONFIANZA=` con comentario en español ("Proveedores de correo de confianza para los genes dominio_externo y mismatch_dominio_url, coma-separada; default en codigo (research D5)")

## Phase 2: Foundational (bloquea US1)

> Los pesos versionados son prerequisite de toda puntuación: sin `pesos_v1.json` no existe sesgo (AC-SCO-01) ni versión (AC-SCO-03).

- [ ] T004 Crear `data/pesos/pesos_v1.json` con los 32 pesos **literales** de `PESOS_AG` actuales (sin redondear), `"sesgo": -1.0`, `"version": "pesos_v1"`, `"fecha": "2026-10-27"`, `"conjunto_entrenamiento": "100correos.csv (corpus CEAS_08, vectores de 32 genes + label, aportado por el usuario)"`, `"semilla": 42` y nota `[VERIFICAR]` sobre fecha/semilla originales del entrenamiento GA (data-model.md §PesosGeneticos)
- [ ] T005 [P] Escribir **rojo** `tests/unit/test_pesos.py`: carga del JSON real (32 claves exactas de `MAPEO_INDICES`, `version == "pesos_v1"`, `sesgo == -1.0`), rechazo de JSON faltante/ilegible/schema inválido con `PesosError` (Art. III.9), cache de proceso (segunda lectura no relee disco: usar `tmp_path` + contador o `mtime`), y validador de claves de más y de menos — marcar `@pytest.mark.ac("AC-SCO-03")` solo la aserción de versión
- [ ] T006 Implementar `src/level3_logic/pesos.py`: modelo Pydantic `PesosGeneticos` (campos y validaciones literales del data-model.md: `pesos` con **exactamente** las 32 claves de `MAPEO_INDICES` vía `model_validator`, faltantes/sobrantes ⇒ error), `PesosError(ScoringError)` y `cargar_pesos(ruta: Path | None = None) -> PesosGeneticos` con cache de proceso y default `data/pesos/pesos_v1.json` (raíz del proyecto resuelta relativa a la ubicación del módulo, no al cwd) — ejecutar `python -m pytest tests/unit/test_pesos.py -q` hasta verde

## Phase 3: User Story 1 — Score final que combina genético + banderas (P1)

**Goal**: `score_final = min(100, score_genetico_con_sesgo + min(60, puntos_banderas))` reproducible, con pesos versionados y corrección de los defectos M10 (FR-001..FR-007).

**Independent Test Criteria**: un correo con genes y banderas conocidos produce el `score_final` esperado, con `version_pesos` guardado; ninguna propiedad de monotonicidad ni los límites 59/60/61 y 99/100/101 fallan; "urgente" no coincide dentro de "insurgente".

### 3.1 Pruebas rojas (todas [P], archivos distintos)

- [ ] T007 [P] [US1] Escribir `tests/unit/test_ac_sco_01_score_bajo.py`: correo limpio (asunto/cuerpo/banderas sin genes ⇒ matriz de 0 genes) ⇒ `score_genetico < 30` usando `evaluate` con pesos reales (sesgo -1.0 ⇒ esperado 26.89) y además la sigmoide directa con `suma=0`; marcar `@pytest.mark.ac("AC-SCO-01")`
- [ ] T008 [P] [US1] Escribir `tests/unit/test_ac_sco_06_palabra_completa.py`: "urgente" NO coincide en "insurgente", "verify" NO coincide en "verification..." cuando la palabra no está como token, sí coincide con puntuación pegada ("urgente,"), mayzúsculas y acentos; probar el helper y un gen léxico end-to-end (asunto); `@pytest.mark.ac("AC-SCO-06")`
- [ ] T009 [P] [US1] Escribir `tests/unit/test_genetico_genes.py`: matriz por partición de equivalencia que active los 32 genes por grupos (headers From/Date, asunto, cuerpo, URLs) verificando `genes_implicados`, incluida la FR-005: gene 0 y gene 28 **no** se activan cuando dominios están en `DOMINIOS_PROPIOS`/proveedores de confianza (inyectar `ConfigScoring` de prueba) y sí con dominios desconocidos — esta matriz aporta la cobertura de `genetic_logic.py` modificado (Art. II.3)
- [ ] T010 [P] [US1] Escribir `tests/unit/test_ac_sco_02_monotonicidad.py` con `hypothesis`: para pesos de genes arbitrarios (listas de 32 bits generadas) y puntos de banderas `p` crecientes, `score_final` nunca baja al agregar una bandera (por construcción `puntos_banderas >= 0` y `min(100,·)` no decreciente), incluyendo la saturación en 100; `@pytest.mark.ac("AC-SCO-02")`
- [ ] T011 [P] [US1] Escribir `tests/unit/test_ac_sco_05_limites.py` como **tabla de valores límite**: puntos de banderas 59/60/61 ⇒ `puntos_banderas` 59/60/60 (tope); `score_genetico` y puntos que producen `score_final` 99/100/101 previo a `min(100,…)` ⇒ 99/100/100; `@pytest.mark.ac("AC-SCO-05")`
- [ ] T012 [P] [US1] Escribir `tests/unit/test_ac_sco_03_version.py`: `ScoreFinal.version_pesos == "pesos_v1"` derivado del JSON (no de constante hardcodeada), y que el dict de reporte producido por la lógica de `agent.py` incluye `version_pesos` y `score_genetico` (probar la función de reporte pura existente o el mapeo del scoring, sin LLM); `@pytest.mark.ac("AC-SCO-03")`
- [ ] T013 [P] [US1] Escribir `tests/unit/test_scoring_motor.py`: `calcular_score_final` con **dobles inyectados** de 003/004/005 (`DependenciasScoring` con `cliente_rdap` nulo, `deps_urls` fake, `ahora` fijo — reutilizar `tests/unit/dobles_red.py` y los fixtures RDAP de `conftest.py`): suma de los tres catálogos con tope 60, `origen` correcto en `BanderaScoring`, adjuntos por parámetro (research D7), cero banderas ⇒ `puntos_banderas == 0`, degradación sin red (sin excepción), invariante del `model_validator` de `ScoreFinal` y errores de `ConfigScoring` inválida — **cero red real** (Art. II.5)
- [ ] T014 [US1] Ejecutar `python -m pytest tests/unit/ -k "sco or pesos or genetico" -q` y confirmar el **rojo** por la razón esperada (`ModuleNotFoundError` de `src.level3_logic.scoring` / `pesos` y aserciones de genético sin sesgo) — adjuntar salida en el commit de pruebas (Art. II.1)

### 3.2 Implementación (verde)

- [ ] T015 [US1] En `src/level3_logic/genetic_logic.py`: añadir `contiene_palabra_completa(palabra: str, texto: str) -> bool` (regex compilada `(?<!\w)…(?!\w)` con `re.escape` e `re.IGNORECASE`, research D4) y usarla en `_contiene_alguna` y en los detectores de keywords de URL (FR-004)
- [ ] T016 [US1] En `src/level3_logic/genetic_logic.py`: añadir `ConfigGenetico(pesos: PesosGeneticos, dominios_propios: tuple[str,...] = (), proveedores_confianza: tuple[str,...] = ())` y parámetro keyword `config: ConfigGenetico | None = None` en `evaluate` (default: `cargar_pesos()` + env); aplicar **FR-003** (`score = 100/(1+e^{-(suma + pesos.sesgo)})`; 0 genes ⇒ 26.89), **FR-005** (genes 0 y 28 condicionados a listas) y **FR-006** (retornar también `version_pesos = pesos.version`; eliminar el `PESOS_AG` hardcodeado y el `VERSION_PESOS` constante — la fuente es el JSON; `MAPEO_INDICES` permanece); conservar el shape legacy (`score`, `genes_implicados`, `suma_lineal_ag`) y el docstring en español; el archivo debe quedar < 450 líneas (Art. III.1)
- [ ] T017 [P] [US1] Crear `src/level3_logic/scoring/modelos.py`: `ScoringError`, `BanderaScoring` (`origen: Literal["cabeceras","urls","adjuntos"]`, `codigo`, `puntos ge=0`) y `ScoreFinal` con validaciones literales del data-model.md (`score_final int ge=0 le=100`, `puntos_banderas le=TOPE_PUNTOS_BANDERAS` **importado** de `src.level2_agent.banderas.modelos`, `version_pesos min_length=1`, invariante `score_final == min(100, round(score_genetico + puntos_banderas))` por `model_validator`)
- [ ] T018 [P] [US1] Crear `src/level3_logic/scoring/configuracion.py`: `ConfigScoring` (`dominios_propios`, `proveedores_confianza`, `ruta_pesos`) + constante `PROVEEDORES_CONFIANZA_POR_DEFECTO` (lista D5 de research) + `desde_entorno()` leyendo `DOMINIOS_PROPIOS`, `DOMINIOS_PROVEEDORES_CONFIANZA` y `RUTA_PESOS` (coma-separadas, minúsculas, sin punto inicial; env malformada ⇒ `ScoringError`)
- [ ] T019 [US1] Crear `src/level3_logic/scoring/motor.py`: `DependenciasScoring` (dataclass frozen: `cliente_rdap`, `deps_urls`, `ahora` — defaults de producción) y `calcular_score_final(email_data, config=None, deps=None, adjuntos_analizados=()) -> ScoreFinal` con el orden de 8 pasos del contrato (§3): `cargar_pesos` → `evaluate` → `evaluar_banderas(email_data, ahora=…, cliente_rdap=…)` → `analizar_urls(email_data, deps=…)` → suma de adjuntos inyectados → `min(60, …)` → `min(100, round(…))` → `BanderaScoring` agregados en orden estable; funciones ≤ 40 líneas (Art. III.2); docstring en español citando el contrato
- [ ] T020 [US1] Crear `src/level3_logic/scoring/__init__.py` exponiendo exactamente la superficie del contrato (§1): `calcular_score_final`, `ScoreFinal`, `BanderaScoring`, `ConfigScoring`, `DependenciasScoring`, `ScoringError`, `PesosError`
- [ ] T021 [US1] Cablear en `src/level2_agent/agent.py`: reemplazar el cuerpo de `_genetic_score` por `calcular_score_final(email_data)` (manteniendo fallback `SCORE_FALLBACK=50.0` + log en excepción, con `version_pesos="indeterminada"`), usar `score_final` para el branch 30/75 (umbrales **sin cambiar**), y añadir a `PhishingReport` los campos `score_genetico: float` y `version_pesos: str` poblados en `generate_benign_report`/`generate_malicious_report` (máx. 5 parámetros, Art. III.2; sin tocar prompts ni veredictos — eso es la spec 008)
- [ ] T022 [US1] Ejecutar `python -m pytest tests/unit/ -q` y llevar toda la suite a verde (incluidas las pruebas de 003/004/005, que **no deben** verse afectadas)
- [ ] T023 [US1] Verificar cobertura de lo nuevo y modificado: `python -m pytest tests/unit/ --cov=src/level3_logic/scoring --cov=src/level3_logic/pesos --cov=src/level3_logic/genetic_logic --cov-branch --cov-fail-under=80 -q` ⇒ ≥ 80 % líneas y ramas en los tres (Art. II.3); si `genetic_logic.py` queda corto, ampliar la matriz de T009 (nunca bajar el umbral, Art. II.7)

## Phase 4: Polish & cross-cutting concerns

- [ ] T024 [P] Ejecutar `python scripts/verify.py` completo en la rama y dejar EXIT=0 (lint, tipos, cobertura global, trazabilidad, secretos, longitud, nombre de rama)
- [ ] T025 [P] Ejecutar `python scripts/check_trazabilidad_ac.py --spec specs/007-scoring-genetico/spec.md` ⇒ AC-SCO-01..06 todos cubiertos, exit 0
- [ ] T026 [P] Actualizar `README.md` (aditivo): entrada del árbol para `src/level3_logic/scoring/` y `pesos.py`, y mención de `data/pesos/pesos_v1.json` como fuente de pesos versionados
- [ ] T027 Actualizar `AGENTS.md`: **reemplazar** la nota "Genetic weights are hardcoded… editing the xlsx does nothing" por la nueva realidad (pesos cargados de `data/pesos/pesos_v1.json` vía `cargar_pesos()` con cache; `MAPEO_INDICES` sigue en código; el xlsx sigue sin cargarse) y añadir la nota del módulo `scoring/` (fachada `calcular_score_final`, no wired… wired en `agent.py`, tope 60 importado de 003, env vars) — coherente con el estilo de las notas de 003/004/005
- [ ] T028 Validar el pipeline legado vivo (requiere `GOOGLE_API_KEY`): `python tests/test_pipeline.py`; medir rutas de las 3 fixtures con el scoring nuevo; si `ai_agent` (0 genes) deja de caer en 30–75, **pedir aprobación explícita al usuario** antes de actualizar solo la metadata `_test` de `tests/fixtures/ai_agent.json` (motivo: SC-001 — "sin señales" ya no da 50; research D10); el caso `ai_agent` ya fallaba por causa preexistente (JSON del Gemini) — no confundir regresión con cambio de diseño; **no ejecutar si no hay aprobación** (Art. II.7)
- [ ] T029 AC-SCO-04 + FR-007 (report-only): cuando la rama `test/conjunto-evaluacion` (spec 015) conviva con esta, ejecutar `python scripts/evaluar_desempeno.py --modo grabado` y registrar recall/falsos positivos reales en el informe (si no cumplen ≥95 % / ≤2 %, **no** ajustar umbrales ni pesos); además correlacionar los 32 genes del CSV `data/evaluacion/fuente_entrenamiento/100correos.csv` contra `label` y documentar qué pesos negativos contradicen los datos (p. ej. `apelacion_miedo`) — dejar ambos resultados en `specs/007-scoring-genetico/informe-implantacion.md`
- [ ] T030 Escribir el informe final `specs/007-scoring-genetico/informe-implantacion.md` (Art. IV.3): comando y resultado de pruebas, cobertura (líneas y ramas), lista AC → prueba, y desviaciones (p. ej. adjuntos por inyección D7, `[VERIFICAR]` de calibración del sesgo)

## Dependencies

- **Setup (T001–T003)**: sin dependencias; en paralelo entre sí.
- **Fundacional (T004→T005→T006)**: T004 es dato; T005 (pruebas rojas) antes que T006 (implementación). T006 desbloquea T016 y T019.
- **US1 rojas (T007–T013)**: en paralelo entre sí; todas anteriores a T014 (verificación de rojo) y a la implementación.
- **Implementación**: T015 → T016 (coincidencia antes de config); T017 → T019 (modelos antes de motor); T018 → T019; T020 al final del paquete; T021 después de T019/T020 (wire); T022/T023 al cierre.
- **Polish (T024–T030)**: T024–T027 en paralelo; T028 requiere aprobación del usuario; T029 requiere convivencia con la rama 015 (bloqueo externo, no de esta rama); T030 cierra.

## Parallel Execution Examples

- **Grupo Setup**: `T001 + T002 + T003` — tres archivos distintos (`pyproject.toml`, `scripts/verify.py`, `.env.example`).
- **Grupo rojas US1**: `T007 + T008 + T009 + T010 + T011 + T012 + T013` — siete archivos de prueba independientes.
- **Grupo implementación paquete**: `T017 + T018` en paralelo (modelos y configuración no se tocan); T019 los consume.
- **Grupo polish**: `T024 + T025 + T026 + T027` — compuertas y docs aditivas en archivos distintos.

## Implementation Strategy

**MVP = US1 completa** (es la única historia; el producto no tiene valor parcial sin el score combinado). Orden sugerido: Setup (T001–T003) → fundacional (T004–T006) → rojas US1 (T007–T014) → genético corregido (T015–T016) → paquete scoring (T017–T020) → wire (T021) → verde y cobertura (T022–T023) → polish (T024–T030). Entrega incremental dentro de US1: el scoring es utilizable desde T020 (pruebas verdes) aunque el wire (T021) lo haga visible en el pipeline. Riesgos: (1) carrera por el directorio compartido con sesiones paralelas — commitear pronto y temprano; (2) T028 depende de aprobación humana y T029 de la rama 015 — ninguno bloquea el merge de lo demás; (3) si la cobertura de `genetic_logic.py` queda corta, se amplía la matriz de genes (T009), nunca el umbral.
