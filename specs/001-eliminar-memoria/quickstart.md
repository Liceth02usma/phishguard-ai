# Quickstart: Eliminar Memoria Conversacional del Agente

**Spec**: [spec.md](./spec.md) | **Branch**: `refactor/eliminar-memoria` | **Contrato**: [contracts/eliminar-memoria-cli.md](./contracts/eliminar-memoria-cli.md)

Guía de validación ejecutable. No contiene implementación: la implementación y sus pruebas
se detallan en `tasks.md`.

## Prerrequisitos

```powershell
# Dependencias del proyecto (el código de src/ se importa en las pruebas — research D8)
pip install -r requirements.txt

# Tooling de calidad (ya presente desde la spec 000)
pip install pytest pytest-cov ruff mypy
```

Variables relevantes: las pruebas NO necesitan `GOOGLE_API_KEY` ni
`MONGODB_ATLAS_CLUSTER_URI` (usan dobles). Solo la validación manual opcional (V5) las
necesita.

## V1 — Suite de pruebas con trazabilidad (obligatoria)

```powershell
python -m pytest tests/unit/ -q --cov=scripts --cov-branch --cov-fail-under=80
python scripts/check_trazabilidad_ac.py --spec specs/001-eliminar-memoria/spec.md
```

**Esperado**: cero fallos; cobertura ≥ 80 % sobre `scripts/`; `trazabilidad_ac (4 AC
cubiertos)` — AC-MEM-01..04.

## V2 — Compuertas completas (Art. IV.1)

```powershell
python scripts/verify.py
```

**Esperado**: exit 0. (`dependencias` puede quedar como advertencia no bloqueante: vulns
preexistentes fuera de alcance, ver spec 000 / spec 014.)

## V3 — Ningún rastro de memoria en el código y documentación (AC-MEM-01 / FR-004)

```powershell
# 1) El módulo ya no existe
Test-Path src\level2_agent\memory.py                      # esperado: False

# 2) Búsqueda literal en el código fuente
Select-String -Path src\level2_agent\*.py -Pattern "get_chat_history|MongoDBChatMessageHistory|MEMORY_TOOL|MEMORY_DATABASE|MEMORY_COLLECTION|chat_history"
# esperado: sin resultados

# 3) README y configuración sin textos de memoria
Select-String -Path README.md,AGENTS.md,.env.example -Pattern "memory\.py|memoria conversacional|Chat history"
# esperado: sin resultados
```

Las mismas comprobaciones las ejecuta la prueba `@pytest.mark.ac("AC-MEM-01")`.

## V4 — Independencia de análisis (AC-MEM-02)

```powershell
python -m pytest tests/unit/ -k "independencia" -v
```

**Esperado**: los 5 correos analizados en dos órdenes distintos producen para cada correo
el mismo score, veredicto y banderas (dobles deterministas del modelo; sin red).

## V5 — Migración (AC-MEM-03 / AC-MEM-04)

**Automatizado (dobles, se ejecuta en CI):**

```powershell
python -m pytest tests/unit/ -k "migracion or rag_intacto" -v
```

**Esperado**: filas de la tabla de decisión del contrato verdes — simulación no borra,
`--confirmar` borra por lotes, colección ausente no es error, validación fallida aborta,
`phishguard.docs_phishing` intacto.

**Manual opcional (contra Atlas real — `[VERIFICAR]` si no se ejecuta, research D11):**

```powershell
# Requiere MONGODB_ATLAS_CLUSTER_URI real. SIEMPRE primero en simulación:
python scripts/eliminar_memoria.py          # paso 1: revisar el plan impreso (nada se borra)
python scripts/eliminar_memoria.py --confirmar   # paso 2: solo si el plan es correcto
```

**Esperado**: paso 1 exit 0 sin cambios en Atlas; paso 2 exit 0; en Atlas dejan de existir
las colecciones de `memory-agent` y `phishguard.docs_phishing` conserva todos sus
documentos (comprobar el conteo antes/después).

## V6 — Calidad estática (Art. IV.1d–e)

```powershell
python -m ruff check scripts/ tests/unit/
python -m mypy scripts/ tests/unit/
(Get-ChildItem scripts,tests\unit -Recurse -Filter *.py | ForEach-Object { (Get-Content $_.FullName | Measure-Object -Line).Lines })
```

**Esperado**: `All checks passed!`, `Success: no issues found`, ningún archivo > 500 líneas.

## V7 — Rama (Art. IV.1g)

```powershell
git branch --show-current
python scripts/check_nombre_rama.py
```

**Esperado**: `refactor/eliminar-memoria` y `[PASS] nombre_rama`.
