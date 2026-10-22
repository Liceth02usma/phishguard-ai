# Research: Eliminar Memoria Conversacional del Agente

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `refactor/eliminar-memoria`

Fase 0 del plan. Cada decisión resuelve un desconocido del Technical Context o un
`[VERIFICAR]` de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` (módulo M01). Formato:
Decisión → Rationale → Alternativas consideradas.

---

## D1 — Inventario verificado de usos de memoria (resuelve `[VERIFICAR]` M01)

**Decisión**: el alcance de FR-001/FR-004 es exactamente este inventario, verificado hoy
contra el código (búsqueda `memory|session_id|MessageHistory|historial` en todo el repo):

| Archivo | Líneas | Qué hay que quitar |
|---|---|---|
| `src/level2_agent/memory.py` | archivo completo (19) | **ELIMINAR** el módulo |
| `src/level2_agent/agent.py` | 27 (`from .memory import get_chat_history`), 205 (`chat_history = get_chat_history(...)`), 228–231 (`add_user_message` / `add_ai_message`) | **QUITAR** import y las 4 llamadas |
| `src/level2_agent/models.py` | 33–34 (`MEMORY_DATABASE`, `MEMORY_COLLECTION`) | **QUITAR** las constantes |
| `src/level2_agent/prompts.py` | 11–12 (`MEMORY_TOOL`), 19 (`tools += MEMORY_TOOL`) | **QUITAR** bloque y adición |
| `README.md` | 139 (árbol: `memory.py # Chat history en MongoDB`), 195 (`Vector store y memoria conversacional`) | **EDITAR** (FR-004) |
| `AGENTS.md` | 39 (namespace `memory-agent.memory`) | **EDITAR** (doc afectada, Art. IV.1h) |
| `.env.example` | — | **SIN CAMBIOS**: no existe ninguna variable de memoria (inventario negativo confirmado) |
| `requirements.txt` | — | **SIN CAMBIOS**: ver D3 |
| `tests/` (legacy) | — | **SIN CAMBIOS**: ninguna referencia a memoria |

No hay `RunnableWithMessageHistory` ni ningún otro envoltorio de historial en el repo, y
`session_id` solo aparece en `memory.py`. `agent.py` nunca PASA el historial a
`agent.invoke({"messages": messages})`: la memoria solo se ESCRIBE (líneas 228–231), lo que
confirma el hallazgo D1 del plan maestro (contaminación persistida + dato de correo
almacenado sin necesidad).

**Rationale**: inventario cerrado = alcance cerrado (Art. VI.1). Cualquier referencia futura
a memoria fuera de esta lista sería código no solicitado.
**Alternativas consideradas**: buscar solo en `level2_agent` (rechazada: RF1 dice "el
resto del código"; la búsqueda sobre todo el repo también prueba FR-004).

## D2 — `MEMORY_TOOL` del prompt: dentro de alcance

**Decisión**: se elimina `MEMORY_TOOL` (prompts.py:11–12,19). El resto del prompt NO se toca.

**Rationale**: FR-004 exige quitar "cualquier variable o **texto** de memoria" y FR-001
cubre "toda importación… en el agente y el resto del código". El texto `MEMORY_TOOL`
instruye al modelo a consultar su memoria conversacional — es literalmente texto de memoria.
La asunción de spec "fuera de alcance: cambios al prompt" se interpreta como *sin cambios
de comportamiento del prompt más allá de lo que FR-001/FR-004 obligan a quitar*.
**Alternativas consideradas**: dejar `MEMORY_TOOL` (rechazada: contradice FR-004 de forma
literal); reescribir el prompt entero (rechazada: fuera de alcance, Art. VI.1).

## D3 — `langchain-mongodb` se conserva en requirements.txt

**Decisión**: no se modifica `requirements.txt`. El paquete `langchain-mongodb` sigue
siendo necesario para el RAG (`MongoDBAtlasVectorSearch` en `tools/__init__.py`), que la
spec FR-005 prohíbe tocar. Solo desaparece su uso de `chat_message_histories`.

**Rationale**: RF5/AC-MEM-04 (RAG intacto) — eliminar el paquete rompería `create_retriever`.
**Alternativas consideradas**: quitar `langchain-mongodb` (rechazada: rompe el RAG);
revisar `langchain-community` (rechazada: fuera de alcance, la revisión de dependencias es
de la spec 014).

## D4 — Localización del script de migración

**Decisión**: `scripts/eliminar_memoria.py` (CLI de una sola ejecución, en español,
`snake_case`).

**Rationale**: FR-003 pide "un script de una sola ejecución". Ponerlo en `scripts/` hace
que las compuertas de la spec 000 (ruff, mypy `--strict`, cobertura con `--cov=scripts`)
lo cubran automáticamente, sin tocar `pyproject.toml` (Art. II.7: no se relajan umbrales).
No vive en `src/` porque no es parte del pipeline de análisis (una responsabilidad por
módulo, Art. III.7).
**Alternativas consideradas**: `src/level2_agent/memory_migration.py` (rechazada: heredaría
el nombre del módulo que se elimina y quedaría dentro del paquete del agente);
`manage.py` estilo Django (rechazada: no hay framework, YAGNI).

## D5 — Estrategia de borrado y protección del RAG

**Decisión**:

1. Objetivo: **todas** las colecciones de la base `memory-agent` (históricamente
   `memory-agent.memory`, definida hoy por `MEMORY_DATABASE`/`MEMORY_COLLECTION` que se
   eliminan de `models.py`; el script lleva sus propias constantes `BASE_HISTORIAL` y
   `COLECCION_HISTORIAL`).
2. Prohibido por diseño: el script solo acepta la base `memory-agent`. La base
   `phishguard` (RAG: `docs_phishing` + índice `vector_index`) no está en la lista de
   objetivos y el script aborta si el usuario apunta a otra base (guardia explícita).
3. Validación previa (M01: "tras validar que nada las usa"): antes de borrar, el script
   verifica que `src/level2_agent/memory.py` NO existe; si existe, aborta con error y no
   borra nada.
4. Por colección: borrado **por lotes** (`delete_many` por `_id` ascendente en lotes de
   `TAMANO_LOTE = 1000` documentados, hasta vaciar) y al final `drop()` de la colección.
   Si la colección no existe, se omite sin error (edge case de spec).

**Rationale**: el borrado por lotes resuelve el edge case "colección con millones de
documentos" (no se carga todo en memoria) y el `drop()` final garantiza que la colección
"no existe" después (AC-MEM-03). La guardia de `memory.py` implementa la validación de
M01 con una comprobación determinista y barata. `TAMANO_LOTE` no es un valor de dominio:
es un parámetro de implementación; se define como constante con nombre (Art. III.6) y se
justifica (1000 docs ≈ lotes pequeños, tolerantes a locks y a docs grandes).
**Alternativas consideradas**: `drop()` directo sobre la colección sin borrar por lotes
(rechazada: la spec exige borrado por lotes en edge case; además `drop()` aislado no deja
constancia parcial si se interrumpe); dropear la base entera en un comando (rechazada: la
spec habla de colecciones y exige simulación + confirmación — además `dropDatabase` no
cumple el "borrado por lotes"); cursor con `limit` + `delete_many` por bloques de `_id`
(rechazada en favor del patrón más simple: lotes con `find().sort(_id).limit(TAMANO_LOTE)`
→ `delete_many({_id: {$in: ids}})).

## D6 — Contrato CLI (simulación y confirmación)

**Decisión**: modo **simulación por defecto**; `--confirmar` ejecuta el borrado real;
`--base NOMBRE` no se expone (la base es fija por guardia, D5.2). Exit codes: `0` éxito
(incluye "no había colecciones"), `1` validación fallida o error de conexión. Salida en
español por stdout: qué colección, cuántos documentos y en cuántos lotes (simulación) /
qué se eliminó (real).

**Rationale**: Art. V.2 exige DRY_RUN por defecto en efectos externos; FR-003 exige
"modo de simulación y confirmación explícita" — la bandera `--confirmar` ES la
confirmación explícita (nada se borra sin ella, aunque haya `.env` oAtlas accesible).
**Alternativas consideradas**: prompt interactivo de confirmación (rechazada: el script
debe poder automatizarse en una ventana sin TTY; y una bandera explícita ya cumple FR-003);
variable `DRY_RUN` del entorno (rechazada: mezclaría la semántica de `DRY_RUN` del
poller, que es de otra funcionalidad, con una ejecución única — además DRY_RUN ya está
en `.env` y podría apagar una migración querida por accidente); `--dry-run` como bandera
inversa (rechazada: el default ya es simulación, la bandera sería redundante).
Contrato completo en [`contracts/eliminar-memoria-cli.md`](./contracts/eliminar-memoria-cli.md).

## D7 — Estrategia de pruebas y justificación de técnicas (Art. II.2)

**Decisión**: 5 técnicas (mínimo constitucional: 3), aplicadas así:

| Técnica | Obligatoria | Requisito / prueba |
|---|---|---|
| Partición de equivalencia | — | AC-MEM-01: partición "código con restos de memoria" vs "código limpio" (búsqueda estática sobre `src/`, `README.md`, `.env.example`). AC-MEM-02: partición de correos por ruta (benigna < 30, agente 30–75) para ejercitar la ruta donde existía la memoria |
| Análisis de valores límite | **Sí** (existen umbrales numéricos: `TAMANO_LOTE`) | AC-MEM-03: colección con 0, 1, `TAMANO_LOTE`, `TAMANO_LOTE + 1` y muchos documentos → número exacto de lotes y de borrados |
| Tabla de decisión | **Sí** (el script combina modo × existencia × confirmación) | AC-MEM-03: (simulación × existe) → nada borrado, exit 0; (confirmado × existe) → borrado completo; (cualquier modo × no existe) → exit 0 sin error; (confirmado × `memory.py` existe) → aborta exit 1 |
| Integración con dobles | — | AC-MEM-03/AC-MEM-04: doble de cliente pymongo (`tests/unit/dobles_mongo.py`) que implementa `list_collection_names`, `find`, `delete_many`, `drop`; **nunca** contra Atlas real en CI (Art. II.5) |
| Regresión | — | AC-MEM-02: es la regresión del defecto D1 del plan maestro (contaminación entre correos): analizar 5 correos en 2 órdenes y exigir idéntico score/veredicto/banderas |

**Mecanismo del rojo (AC-MEM-02)**: la prueba elimina `MONGODB_ATLAS_CLUSTER_URI` del
entorno (`monkeypatch.delenv`) y usa un agente ReAct falso con respuestas deterministas +
`create_jira_ticket` simulado. Con el código ACTUAL, la ruta del agente llama
`get_chat_history()` que lanza `ValueError("MONGODB_ATLAS_CLUSTER_URI no está
configurada")` → la prueba **falla por la razón esperada (rojo)**. Tras la eliminación,
`analyze_email` no lee ninguna variable de MongoDB en esa ruta → verde. AC-MEM-01 ya es
roja de entrada porque `memory.py` existe.
**Determinismo**: sin red (dobles), sin hora ni azar; orden de pruebas irrelevante (los
resultados por correo se comparan como conjunto).
**Rationale**: la spec (hint) pide dobles del modelo con respuestas deterministas; las
obligatorias aplican porque hay umbral (`TAMANO_LOTE`) y reglas multi-condición (modo ×
colección × confirmación).
**Alternativas consideradas**: mongomock (rechazada: dependencia nueva para un API de 4
métodos; el doble propio es ~60 líneas y se entiende a la vez); pruebas contra Atlas con
base desechable (rechazada: red real en CI, Art. II.5); `hypothesis` (rechazada: YAGNI,
los límites son finitos y explícitos).

## D8 — Dependencias: instalación local y en CI

**Decisión**:
- Local: instalar `requirements.txt` en el intérprete activo (no hay `.venv` en la máquina;
  las pruebas de esta spec importan `pydantic`, `langchain*`, `langgraph`, `pymongo` — hoy
  ausentes: `test_pipeline.py` ya falla con `ModuleNotFoundError: pydantic`).
- CI: añadir un paso `pip install -r requirements.txt` en `.github/workflows/verify.yml`
  después de instalar el tooling de calidad.

**Rationale**: las pruebas de AC-MEM-02..04 importan código de `src/`; sin dependencias
fallarían en CI con `ModuleNotFoundError`, es decir, la spec no cumpliría Art. IV.1a. La
única alternativa técnica sería marcar pruebas como `skip` si faltan dependencias —
prohibida por Art. II.7 y contraria a IV.1a ("cero skip nuevos"). El workflow es un
artefacto de la spec 000 cuyo propósito es ejecutar `verify.py`; extenderlo con las
dependencias del proyecto es requisito para que las pruebas de ESTA spec corran en CI
(Art. VI.1: se toca lo mínimo indispensable de ese archivo, un solo paso).
**Alternativas consideradas**: `pip install` solo de los paquetes usados (rechazada:
duplicaría `requirements.txt` y se desincronizaría); pruebas sin importar `src/`
(rechazada: AC-MEM-02 exige analizar correos de verdad).

## D9 — Cobertura (Art. II.3) sin tocar la compuerta

**Decisión**: el código ejecutable NUEVO de la spec es `scripts/eliminar_memoria.py` +
`tests/unit/dobles_mongo.py` (código de prueba); ambos quedan dentro de `--cov=scripts`
/ `tests/unit/` que la compuerta de spec 000 ya mide con `--cov-branch`. Los cambios en
`src/level2_agent/` son **exclusivamente eliminaciones** (imports, llamadas y constantes
removidas) — no añaden líneas ni ramas ejecutables nuevas que medir. La compuerta NO se
modifica (ni `fail_under`, ni el flag de `verify.py`).

**Rationale**: Art. II.3 pide ≥ 80 % sobre "código nuevo o modificado"; el único código
modificado ejecutable es la eliminación de llamadas (cuya ruta queda cubierta por las
pruebas de AC-MEM-02) y el único nuevo es el script (cubierto al 100 % objetivo por sus
propias pruebas de tabla de decisión). Art. II.7 prohíbe bajar umbrales — no se toca
ninguno.
**Alternativas consideradas**: extender `--cov` a `src/` (rechazada: modificar la compuerta
de la spec 000 + la cobertura de `src/` legado arrastraría el umbral de todo el repo,
afectando specs futuras — fuera del alcance de FR-001..005).

## D10 — Documentación afectada (Art. IV.1h)

**Decisión**: README (árbol + bullet de MongoDB), AGENTS.md (namespace de memoria; es la
guía de agentes del repo y quedaría desactualizada). `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`
y `docs/specs.md` NO se editan: son documentos de origen/histórico que describen el estado
previo y las specs (M01 sigue siendo verdad como descripción histórica).
**Rationale**: FR-004 exige README y configuración; IV.1h exige la documentación afectada;
tocar los docs fuente rompería la trazabilidad del plan maestro.
**Alternativas consideradas**: editar también el plan maestro (rechazada: es el input de
las specs, no documentación de uso del producto).

## D11 — `[VERIFICAR]` restantes (Art. VI.3)

- **Puntuaciones del genético para el correo de prueba en banda de agente (30–75)**: se
  confirma empíricamente al escribir AC-MEM-02 (se elige/reconstruye un correo cuyo score
  caiga en esa banda). Si ningún fixture legado cae en la banda, se construye un correo
  sintético mínimo; el valor NO se inventa, se mide con `genetic_logic`.
- **Borrado real contra Atlas**: solo validación manual opcional en quickstart con
  `MONGODB_ATLAS_CLUSTER_URI` real y SIEMPRE primero en modo simulación (las pruebas de CI
  usan dobles). Se marcará `[VERIFICAR]` en el informe final si no se ejecuta.

---

## Resolución de desconocidos

| Desconocido del Technical Context | Estado |
|---|---|
| Dónde se usa la memoria (M01 `[VERIFICAR]`) | ✅ D1 — inventario cerrado |
| Cómo validar que nada la usa antes de borrar | ✅ D5.3 — guardia sobre `memory.py` |
| Estrategia de borrado con millones de docs | ✅ D5.4 — lotes de 1000 + drop |
| Simulación / confirmación del script | ✅ D6 — default simulación, `--confirmar` |
| Técnicas de prueba (Art. II.2) y rojo de AC-MEM-02 | ✅ D7 — 5 técnicas + mecanismo de rojo |
| Dependencias locales y de CI | ✅ D8 — instalar requirements en ambos |
| Cobertura sin relajar compuertas | ✅ D9 |
| Documentación a actualizar | ✅ D10 |

Sin `NEEDS CLARIFICATION` pendientes → se aprueba Phase 1.
