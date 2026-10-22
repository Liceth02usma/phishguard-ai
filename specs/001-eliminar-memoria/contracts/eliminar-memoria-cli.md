# Contract: CLI de migración `scripts/eliminar_memoria.py`

**Spec**: [spec.md](./spec.md) (FR-003, AC-MEM-03, AC-MEM-04) | **Research**: [research.md](./research.md) (D5, D6)

Contrato de interfaz de la única superficie externa nueva de esta spec: el script de una
sola ejecución que elimina las colecciones de historial de chat de MongoDB.

## Uso

```powershell
# 1) Siempre primero: modo simulación (DEFAULT) — no borra nada
python scripts/eliminar_memoria.py

# 2) Ejecución real — requiere confirmación explícita
python scripts/eliminar_memoria.py --confirmar
```

## Parámetros

| Parámetro | Requiere | Significado |
|---|---|---|
| *(ninguno)* | — | Modo simulación: informa qué se borraría; **cero** escrituras |
| `--confirmar` | todo lo anterior válido | Ejecuta el borrado real por lotes |
| `-h` / `--help` | — | Ayuda estándar, exit 0 |

No hay bandera para cambiar la base: el objetivo es fijo (`memory-agent`) por guardia
(Art. VI.2: no se inventan valores; FR-005 prohíbe tocar el RAG).

## Requisitos previos

- Variable de entorno `MONGODB_ATLAS_CLUSTER_URI` presente (se lee solo de entorno,
  Art. V.3; el script jamás la imprime).
- `src/level2_agent/memory.py` **no** debe existir (validación previa, research D5.3).

## Códigos de salida (exit codes)

| Código | Condición | Escrituras realizadas |
|---|---|---|
| `0` | Simulación completada, o borrado real completado, o no había colecciones de historial (edge case de spec) | `0` en simulación; borrado total en ejecución real |
| `1` | Validación fallida (`memory.py` existe, base no es la objetivo, falta `MONGODB_ATLAS_CLUSTER_URI`) o error de conexión/persistencia | **0** (aborta antes de escribir) |

## Comportamiento (tabla de decisión — verificada por pruebas)

| # | `--confirmar` | Colecciones en `memory-agent` | `memory.py` | Acción | Exit |
|---|---|---|---|---|---|
| 1 | no | alguna con N > 0 docs | no | imprime plan: colección, N docs, `⌈N/TAMANO_LOTE⌉` lotes; nada se borra | 0 |
| 2 | no | vacía o base inexistente | no | informa "nada que eliminar"; exit 0 sin error | 0 |
| 3 | sí | alguna con N > 0 docs | no | borra por lotes (`TAMANO_LOTE = 1000`) y `drop()` por colección; informa lotes y totales | 0 |
| 4 | sí | vacía o base inexistente | no | informa "nada que eliminar" (sin error) | 0 |
| 5 | cualquiera | cualquiera | **existe** | aborta ANTES de cualquier escritura con mensaje indicando que la validación falló | 1 |
| 6 | sí | cualquier objetivo no sea `memory-agent` | no | aborta con mensaje (guardia de protección del RAG) | 1 |

**Invariantes** (comprobados en todas las filas):

- I1: la base `phishguard` (RAG: `phishguard.docs_phishing`) no recibe ninguna operación
  de escritura — AC-MEM-04.
- I2: sin `--confirmar` no existe ninguna llamada a `delete_many` ni `drop` — AC-MEM-03
  (parte simulación).
- I3: con `--confirmar`, tras la ejecución las colecciones de `memory-agent` no existen —
  AC-MEM-03 (parte migración).
- I4: la salida es en español, por stdout (errores por stderr), y no contiene secretos ni
  datos de correos (Art. V.3/V.4) — solo nombres de base/colección y conteos.

## Constantes del contrato

| Constante | Valor | Origen |
|---|---|---|
| `BASE_HISTORIAL` | `memory-agent` | `models.py: MEMORY_DATABASE` (estado actual, D1) |
| `COLECCION_HISTORIAL` | `memory` (información informativa; el script enumera TODAS las colecciones de la base) | `models.py: MEMORY_COLLECTION` |
| `TAMANO_LOTE` | `1000` | parámetro de implementación, research D5 — constante con nombre (Art. III.6) |

## Relación con la constitución

- Art. V.2: simulación por defecto; el efecto externo (borrado) lo decide la bandera
  explícita del operador, nunca un modelo.
- Art. III.9: todo fallo sale por stderr con mensaje y exit 1; sin `except:` desnudo.
- Art. II.6: cada fila de la tabla de decisión queda cubierta por pruebas marcadas
  `AC-MEM-03` / `AC-MEM-04`.
