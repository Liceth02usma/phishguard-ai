# Research: Scoring con Clasificador Lineal y Banderas (spec 007)

**Fecha**: 2026-10-28 · **Rama**: `feature/scoring-genoring-genetico`

Fuentes: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` M10, `src/level3_logic/genetic_logic.py` (estado actual), APIs de specs 003/004/005, contrato spec 012, spec 015 (conjunto etiquetado).

## D1 — Composición de `puntos_banderas` (catálogos 5.1 + 5.2 + 5.3)

**Decisión**: `puntos_banderas = min(60, puntos_totales_003 + Σ puntos_urls_004 + Σ puntos_adjuntos_005)`, reutilizando `TOPE_PUNTOS_BANDERAS` importado de `banderas/modelos.py`.

**Rationale**: la spec declara `Depende de: 03, 04, 05` y M10 define "catálogo de la sección 5 con tope de 60" — la sección 5 contiene los tres catálogos.

**Alternativas consideradas**: solo 003 (rechazada: ignora deps), solo 003+004 (rechazada: sin razón para excluir 5.3).

## D2 — Clasificador lineal en vez de algoritmo genético

**Decisión**: reemplazar `PESOS_AG` hardcoded + sigmoide con sesgo por un clasificador lineal cuyos coeficientes provienen de una regresión logística entrenada sobre `100correos.csv`. En runtime: `score_clasificador = 100 × σ(Σ wᵢ·geneᵢ + b)` — producto punto en Python puro, cero dependencias nuevas. El intercepto `b` del modelo reemplaza el sesgo configurable de la spec anterior.

**Rationale**: el usuario solicitó explícitamente "reemplazemoslo por un clasificador lineal ya entrenado y accesible en correos en español para no complicarnos y gratuito". La regresión logística sobre las mismas 32 características produce coeficientes con signos correctos (a diferencia de los pesos negativos del AG para señales de riesgo), el intercepto garantiza AC-SCO-01 (0 genes → score bajo), y la inferencia es un simple dot product sin sklearn en runtime.

**Alternativas consideradas**:
- Mantener AG con sesgo configurable (rechazada: decisión del usuario).
- Red neuronal o SVM (rechazada: "no complicarnos"; más dependencias y complejidad).
- API externa de clasificación (rechazada: "gratuito" + dependencia de red + latencia).

## D3 — Modelo versionado como JSON validado (FR-006)

**Decisión**: `data/modelo/clasificador_v1.json` con schema Pydantic (`ClasificadorLineal` en `src/level3_logic/modelo.py`): `version` (str), `fecha` (ISO), `conjunto_entrenamiento` (str), `hiperparametros` (dict: solver, C, max_iter, random_state), `metricas_entrenamiento` (dict: accuracy, recall, f1), `intercepto` (float), `coeficientes` (dict: exactamente 32 claves de `MAPEO_INDICES` → float). Carga con cache de proceso; archivo ausente/inválido ⇒ `ModeloError`.

**Rationale**: el JSON es el contrato entre el entrenamiento offline y el runtime; la validación Pydantic garantiza que los 32 coeficientes coinciden con los genes; el cache evita re-lectura; el fallo ruidoso sigue Art. III.9.

**Alternativas consideradas**:
- joblib/pickle (rechazada: formato binario opaco, riesgos de seguridad, dependencia de sklearn).
- `pesos_v1.json` anterior (rechazada: schema distinto — ahora hay intercepto + metadata de entrenamiento).

## D4 — Coincidencia por palabra completa (FR-004)

**Decisión**: helper `contiene_palabra_completa(palabra, texto)` en `genetic_logic.py` usando regex compilada `(?<!\w)palabra(?!\w)` con `re.IGNORECASE` y `re.escape`.

**Rationale**: sin dependencias nuevas; resuelve "urgente" ⊄ "insurgente" (AC-SCO-06).

**Alternativas consideradas**: tokenización con `split()` (rechazada: falla con puntuación pegada), librería NLP (rechazada: cero deps nuevas).

## D5 — Listas de dominios propios y de confianza (FR-005)

**Decisión**: `ConfigScoring.desde_entorno()` lee `DOMINIOS_PROPIOS` (reutiliza env de 003) y `DOMINIOS_PROVEEDORES_CONFIANZA` (nueva, default constante con proveedores mayoritarios + transaccionales). Genes 0 y 28 condicionados a listas.

**Rationale**: M10 "relativizar usando listas"; reutiliza env de 003 para coherencia.

## D6 — Cableado en `agent.py` (contrato 012)

**Decisión**: `analyze_email()` llama `calcular_score_final(email_data)`; `PhishingReport` gana `score_clasificador` y `version_modelo` (campos del contrato 012). Fallback: `SCORE_FALLBACK=50.0` + `version_modelo="indeterminada"` + log error.

**Rationale**: el contrato 012 exige `score` (final), `score_clasificador` ("spec 007") y `version>modelo` (requerido). Sin cableado, AC-SCO-03 no se cumple en producto.

## D7 — Puntos de adjunto por parámetro inyectable

**Decisión**: `calcular_score_final(..., adjuntos_analizados=())`. El pipeline aporta lista vacía (models.Adjunto no retiene payload). [VERIFICAR]: spec posterior puede pasar análisis real.

**Rationale**: respeta 005 sin tocar `models.py`/`normalizacion/`; pruebas inyectan `AnalisisAdjunto` reales.

## D8 — Compuertas de calidad (aditivas)

**Decisión**: `pyproject.toml` override mypy-strict para `src.level3_logic.scoring*` y `src.level3_logic.modelo`; `scripts/verify.py` añade `--cov` y RUTAS para `scoring/`, `modelo.py` y `genetic_logic.py`. `genetic_logic.py` NO entra a ruff/mypy estricto (modificación funcional con estilo legado).

## D9 — Estructura del paquete

**Decisión**: `src/level3_logic/scoring/` (motor, modelos, configuracion, __init__) + `src/level3_logic/modelo.py` (fuera del paquete para evitar ciclos). `genetic_logic.py` modificado in-place (única fuente de extracción de genes).

## D10 — Conflicto de fixture `ai_agent.json` (Art. II.7)

**Decisión**: con el clasificador entrenado, 0 genes → score bajo (< 30) por diseño del modelo. La fixture `ai_agent` puede cambiar de ruta → actualizar metadata `_test` **solo con aprobación del usuario** (Art. II.7).

## D11 — Procedimiento de entrenamiento offline

**Decisión**: script `scripts/entrenar_clasificador.py` que: (1) lee `data/evaluacion/fuente_entrenamiento/100correos.csv` (32 columnas de genes + label), (2) entrena `LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, random_state=42)`, (3) valida que 0 genes → score < 30, (4) exporta `data/modelo/clasificador_v1.json` con coeficientes, intercepto y metadata. El script corre **antes** de la implementación del runtime (prerequisite de T004); no es parte del pipeline.

**Rationale**: "ya entrenado" = el modelo existe antes del deploy; el script es la herramienta que lo produce; scikit-learn es dependencia de desarrollo, no de runtime.

## D12 — Ubicación del modelo

**Decisión**: `data/modelo/clasificador_v1.json` (directorio nuevo `data/modelo/`, paralelo a `data/pesos/` y `data/evaluacion/`).

## D13 — Garantía de AC-SCO-01 con el modelo entrenado

**Decisión**: el script de entrenamiento verifica que `score_clasificador(genes=0) < 30` y falla si no se cumple. Si la regresión logística estándar no lo garantiza (p. ej. por desbalance de clases), se ajusta `class_weight='balanced'` o se agrega un intercepto calibrado. El resultado se documenta en `metricas_entrenamiento`.

**Rationale**: AC-SCO-01 es un requisito duro; el entrenamiento debe producir un modelo que lo satisfaga.

## Incógnitas restantes ([VERIFICAR])

1. **Coeficientes reales del modelo** — se generan al ejecutar `scripts/entrenar_clasificador.py`; hasta entonces, el JSON no existe.
2. **AC-SCO-04** — requiere convivencia con la rama `test/conjunto-evaluacion` (spec 015); report-only.
3. **Aporte de banderas 003 a los fixtures** — se mide en implementación (D10).
