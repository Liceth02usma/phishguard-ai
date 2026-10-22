# Data Model: Eliminar Memoria Conversacional del Agente

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## 1. Entidades de MongoDB (estado ANTES de la spec)

### 1.1 Base a ELIMINAR — historial de chat

| Campo | Valor | Origen |
|---|---|---|
| Base | `memory-agent` | `models.py: MEMORY_DATABASE` (se elimina en FR-001) |
| Colección | `memory` | `models.py: MEMORY_COLLECTION` (se elimina en FR-001) |
| Escritor | `memory.py → MongoDBChatMessageHistory(session_id=...)` | `agent.py:205,228–231` |
| `session_id` | `email_data.message_id` (un documento por correo analizado) | `agent.py:205` |
| Contenido persistido | mensajes de usuario/IA del análisis (datos de correo) | `agent.py:228–231` |

Constantes re-declaradas en `scripts/eliminar_memoria.py` (Art. III.6):
`BASE_HISTORIAL = "memory-agent"`, `COLECCION_HISTORIAL = "memory"`.

### 1.2 Base a PRESERVAR — RAG (FR-005 / AC-MEM-04)

| Campo | Valor | Origen |
|---|---|---|
| Base | `phishguard` | `models.py: VECTOR_DATABASE` |
| Colección | `docs_phishing` (`phishguard.docs_phishing`) | `models.py: VECTOR_COLLECTION` |
| Índice | `vector_index` | `models.py: VECTOR_INDEX` |
| Uso | `MongoDBAtlasVectorSearch` retriever del agente | `tools/__init__.py` |

**Regla de protección**: el script de migración solo acepta `BASE_HISTORIAL`; cualquier
otra base → error, exit 1, cero borrados (guardia, research D5.2).

### 1.3 Modelo de correo y reporte — SIN CAMBIOS

`EmailData` (`htmlBody`, `headers`, `subject`, `recipient`, `textBody`, `message_id`) y
`PhishingReport` (`resumen`, `analisis_tecnico`, `indicadores_phishing`, `es_phishing`,
`nivel_severidad`, `justificacion_veredicto`) no se modifican. El campo `message_id` de
`EmailData` se conserva (identifica el correo); deja de usarse como `session_id`.

## 2. Estado del script de migración (máquina de estados)

```
                 ┌──────────────────────────────────────────────┐
                 │                                              │
 [inicio] → VALIDACIÓN → SIMULACIÓN (default) ──exit 0──→ [fin]
                 │            │
                 │            └── con --confirmar ──→ BORRADO POR LOTES ──exit 0──→ [fin]
                 │
                 ├── falla (memory.py existe, base no es memory-agent,
                 │         error de conexión) ──exit 1──→ [fin]
                 │
                 └── no hay colecciones ──exit 0 (sin error)──→ [fin]
```

| Estado | Transición | Condión | Efecto observado |
|---|---|---|---|
| VALIDACIÓN | → SIMULACIÓN | sin `--confirmar` y todo válido | imprime plan de borrado; **ningún** `delete_many`/`drop` (AC-MEM-03, parte simulación) |
| VALIDACIÓN | → BORRADO | con `--confirmar` y todo válido | borrado por lotes + `drop` por colección (AC-MEM-03) |
| VALIDACIÓN | → error | `memory.py` existe, base ajena o `MONGODB_ATLAS_CLUSTER_URI` ausente | mensaje de error en stderr, **cero** operaciones de escritura, exit 1 |
| BORRADO | → fin | todas las colecciones objetivo vaciadas y eliminadas | colecciones de `memory-agent` inexistentes; `phishguard` intacta (AC-MEM-04) |

## 3. Reglas de validación (del script)

| # | Regla | Origen | Violación |
|---|---|---|---|
| V1 | `src/level2_agent/memory.py` NO debe existir | M01 "tras validar que nada las usa" | exit 1, nada borrado |
| V2 | La base objetivo es `memory-agent` (constante fija) | FR-005, research D5.2 | exit 1, nada borrado |
| V3 | `MONGODB_ATLAS_CLUSTER_URI` presente en entorno | existente (`memory.py:10-12` era el patrón) | exit 1 con mensaje |
| V4 | Colección inexistente → se omite sin error | Edge case spec | exit 0 |
| V5 | Colección con N docs → se borran en `⌈N / TAMANO_LOTE⌉` lotes | Edge case spec | — |
| V6 | Base `phishguard` sin tocar en cualquier rama | FR-005, AC-MEM-04 | cualquier cambio = fallo de prueba |

## 4. Modelo de prueba (dobles)

### 4.1 Doble de cliente Mongo — `tests/unit/dobles_mongo.py`

Interfaz mínima de pymongo que consume el script (nada más se implementa):

```text
FakeClienteMongo
├── __init__(bases: dict[str, dict[str, list[dict]]])   # {base: {coleccion: [docs]}}
├── get_database(nombre) -> FakeBase
└── close()

FakeBase
├── list_collection_names() -> list[str]
└── get_collection(nombre) -> FakeColeccion

FakeColeccion
├── count_documents(filtro) -> int
├── find(filtro).sort(campo, 1).limit(n) -> iterable de docs con "_id"
├── delete_many(filtro) -> objeto con .deleted_count
└── drop()                                        # elimina la colección de la estructura
```

Estado observable por las pruebas: estructura dict subyacente (¿existía la colección?,
¿cuántos documentos quedan?, ¿sigue `docs_phishing`?).

### 4.2 Doble del agente ReAct (AC-MEM-02)

- `agent._get_react_agent` → fijo que devuelve `invoke({"messages": ...})` con un
  `AIMessage` JSON determinista (mismo input → misma respuesta, independiente del orden).
- `agent.create_jira_ticket` → falso sin red (Art. V.2: los tickets no se crean en pruebas).
- `MONGODB_ATLAS_CLUSTER_URI` → eliminada del entorno (rojo pre-cambio, research D7).

## 5. Identidad de los resultados de AC-MEM-02

Para cada correo `i` y cada orden de análisis `orden ∈ {A, B}`:

```text
resultado[i] = (score_genetico, report.es_phishing, report.nivel_severidad,
                tuple(report.indicadores_phishing))
assert resultado_A[i] == resultado_B[i]   # para los 5 correos
```

`score_genetico` viene de `_genetic_score` (determinista, sin estado compartido);
`es_phishing`/`nivel_severidad`/`indicadores_phishing` del reporte devuelto. Si el código
volviera a leer o escribir estado entre correos, la igualdad se rompería → la prueba
detecta la regresión del defecto D1.
