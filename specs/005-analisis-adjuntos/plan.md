# Implementation Plan: Análisis Estático de Adjuntos

**Branch**: `feature/analisis-adjuntos` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-analisis-adjuntos/spec.md`

## Summary

Construir un paquete determinista `src/level2_agent/adjuntos/` que, partiendo de los
bytes en memoria de cada adjunto (producidos por la normalización de la spec 002),
calcule hashes (SHA-256 principal; MD5 y SHA-1 informativos), detecte el tipo real por
firma (*magic bytes*, `filetype`) y lo compare con la extensión y el `Content-Type`
(`ADJ_TIPO_NO_COINCIDE`), evalúe la lista configurable de extensiones de riesgo, doble
extensión y HTML/SVG (`ADJ_EXTENSION_RIESGO`, `ADJ_DOBLE_EXTENSION`, `ADJ_HTML`),
detecte macros y vínculos externos en Office (`oletools`/olevba tras interfaz + escaneo
de relaciones OOXML `TargetMode="External"`: `ADJ_MACRO`, `ADJ_ENLACE_EXTERNO`), acciones
peligrosas en PDF (`pypdf` de solo lectura + escaneo crudo de `/JavaScript`,
`/OpenAction`, `/Launch`: `ADJ_PDF_ACTIVO`) y analice zips con límites duros de 100
entradas, 100 MB descomprimidos y relación 100:1, con cifrado detectado por flag
(`ADJ_CIFRADO`, `ADJ_ARCHIVO_SOSPECHOSO`) — el catálogo 5.3 con sus 9 códigos `ADJ_*`,
severidades y puntos queda como constante nombrada. Todo ocurre **solo en memoria**:
nunca se escribe el adjunto a disco con su nombre original, nunca se ejecuta ni se abre
con aplicaciones del sistema (FR-006, Art. V.5), y los archivos maliciosos de prueba
(EICAR, zip bomb, ejecutable renombrado) **se generan en memoria**, no se guardan en el
repositorio (SC-003). Patrones: Strategy (un detector por familia) + Registry (motor
ordenado) + Adapter (olevba tras `Protocol`). Tres dependencias de producción nuevas
fijadas, todas puras en Python: `filetype==1.2.0`, `oletools==0.60.2`, `pypdf==6.21.2`.
TDD con rojo confirmado; 6 técnicas de prueba (valores límite y tabla de decisión, ambas
obligatorias, más partición, propiedades con `hypothesis`, seguridad/AST y regresión) y
trazabilidad AC-ADJ-01..06. Sin cambios en `agent.py`, el poller ni `models.py`: el
consumo de hashes y banderas lo hacen las specs 006 (VirusTotal por hash) y 008
(reglas duras) — research D10.

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10; `pypdf`
requiere ≥ 3.9)

**Primary Dependencies**: pydantic y la stdlib (`hashlib`, `zipfile`, `io`, `email`)
ya presentes; NUEVAS dependencias de producción fijadas: `filetype==1.2.0` (magic
bytes, MIT, sin dependencias), `oletools==0.60.2` (olevba, BSD), `pypdf==6.21.2`
(PDF de solo lectura); tooling: pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks;
`hypothesis` (ya fijada) para propiedades sobre bytes y nombres arbitrarios

**Storage**: N/A — todo el análisis es en memoria (`io.BytesIO`); nada se persiste ni
se escribe a disco (FR-006); la persistencia de análisis llega en spec 11

**Testing**: pytest con `@pytest.mark.ac("AC-ADJ-NN")`, valores límite sobre los
umbrales zip (99:1/100:1/101:1, 100/101 entradas, tope 100 MB), tabla de decisión
(extensión × tipo real × disposición → banderas), dobles (`AnalizadorOffice` falso;
cero red), verificación estática AST de que el paquete no escribe ni ejecuta, cero
archivos en un tmpdir tras analizar; `--cov --cov-branch` sobre `scripts/` y el paquete
nuevo; ruff y `mypy --strict` sobre el código nuevo

**Target Platform**: Windows local + Linux CI (GitHub Actions `verify.yml`); por eso
`filetype` y no `python-magic` (lib nativa `libmagic`, problemática en Windows)

**Project Type**: librería dentro de `src/` (paquete `adjuntos`) consumida por las
specs 006 (consulta VT por hash) y 008 (reglas duras del motor de decisión); sin
endpoint ni binario propio

**Performance Goals**: análisis estático por adjunto en memoria, sin E/S y sin red;
una zip bomb se **aborta antes** de descomprimir en memoria (lee por streaming con
tope duro de bytes: AC-ADJ-04/SC-002); límite heredado de spec 002: ≤ 20 adjuntos por
correo, ≤ 25 MiB por mensaje

**Constraints**: determinismo (mismo payload + config → mismo resultado; sin hora ni
azar); FR-006: cero escritura a disco con nombre original, cero ejecución, cero
aperturas con aplicaciones del sistema; ningún `.py` > 500 líneas (objetivo 300);
funciones ≤ 40 líneas y ≤ 5 parámetros; `mypy --strict` (Art. III.4)

**Scale/Scope**: ~10 módulos nuevos en `src/level2_agent/adjuntos/`, ~11 archivos de
prueba en `tests/unit/`, 3 dependencias de producción nuevas fijadas, extensión de las
compuertas de `verify.py`/`pyproject.toml` al paquete nuevo y extensión de
`.env.example` con la configuración M05. Nada fuera de
`specs/005-analisis-adjuntos/` y de esos archivos; **sin** cambios en `agent.py`,
`prompts.py`, el poller ni `models.py` (research D10/D9)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS | `feature/analisis-adjuntos` creada desde `main` (5fbcd36) antes de cualquier documento o código de la spec; cumple regex Art. I.2 |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | Commits `feat|test|docs: ... (AC-ADJ-NN)` en la rama; nada se escribe en main |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase TDD dedicada en tasks.md; rojo verificado contra un paquete inexistente |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 6 técnicas en `research.md` D11: valores límite (obligatorio: 99/100/101 de relación, 100/101 entradas, tope 100 MB, bytes 0), tabla de decisión (obligatorio: extensión × tipo real × disposición), partición de equivalencia (familias de archivo), propiedades con `hypothesis` (nunca excepción no controlada; hashes ≡ `hashlib`), seguridad y verificación AST (nombres hostiles `..`/rutas; sin escritura/ejecución: AC-ADJ-05/06), regresión (`test_pipeline.py` verde) |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | `verify.py` y `pyproject.toml` se EXTENDEN para medir `src/level2_agent/adjuntos/` (extensión de compuertas, no bajada de umbral; mismo mecanismo de las specs 002/003) |
| II.4 | Sin pruebas sin `assert` | PASS | Toda prueba verifica hashes, banderas, detalles, abortos o la ausencia de archivos en disco |
| II.5 | Sin red real ni hora ni azar sin controlar | PASS | Sin ninguna llamada de red en la spec (VirusTotal es la 006); EICAR, zip bombs, ejecutables y PDFs maliciosos se GENERAN en memoria en las pruebas (SC-003); PRNG con semilla fija para datos incompressibles |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-ADJ-01..06")`; verificado con `scripts/check_trazabilidad_ac.py --spec specs/005-analisis-adjuntos/spec.md` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica ninguna prueba existente; `fail_under` no baja (el código nuevo se prueba completo) |
| III.1 | Archivos `.py` ≤ 500 líneas (objetivo 300) | PASS | 10 módulos por familia de detección; estimado cada uno < 200 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Detectores puros de 1 regla c/u; la API pública recibe `(nombre, tipo_declarado, payload, config)` (4 parámetros) |
| III.3 | `snake_case` en español sin tildes | PASS | `analizar_adjunto`, `detectar_por_firma`, `ConfigAdjuntos`, `ADJ_LIMITE_ENTRADAS_ZIP` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict` ampliado al paquete nuevo; `AnalisisAdjunto`/`ConfigAdjuntos` Pydantic; docstrings en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Strategy (un detector por familia), Registry (motor ordenado) y Adapter (olevba tras `Protocol`), nombrados en `research.md` D2/D3; nada más |
| III.6 | Sin números ni cadenas mágicas | PASS | `ADJ_LIMITE_ENTRADAS_ZIP = 100`, `ADJ_LIMITE_DESCOMPRIMIDO_ZIP = 100 MiB`, `ADJ_RATIO_MAXIMO_ZIP = 100`, catálogo 5.3 como dict nombrado; las listas de extensiones son configuración (`ConfigAdjuntos`) con defaults documentados del M05 |
| III.7 | Una responsabilidad por módulo | PASS | Un módulo por familia (hashes, firma, extensiones, office, pdf, comprimidos); el motor solo orquesta; olevba vive tras su interfaz |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | Las 3 dependencias nuevas se agregan con versión fija; ruff/mypy sobre el paquete nuevo |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` vacíos: cada detector degrada a `detalle` + bandera (p. ej. PDF no parseable → `ADJ_ARCHIVO_SOSPECHOSO`, V.1), nunca silencia; `ConfiguracionError` propio ante config inválida |
| IV.1a–i | Definición de terminado | PASS | verify.py exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar | PASS | Archivo no inspeccionable (PDF inválido, zip truncado, zip que excede límites) → `ADJ_ARCHIVO_SOSPECHOSO`, nunca "sin indicadores"; la spec no emite veredictos (specs 007/008) |
| V.2 | Acciones externas por código determinista | PASS | Sin acciones externas y sin red alguna en la spec |
| V.3 | Secretos fuera de reposo | PASS | Sin claves nuevas; las pruebas no leen `.env`; nada de `.env` se registra en logs |
| V.4 | PII enmascarada antes de persistir/enviar a terceros | PASS | Nada se persiste ni se envía a terceros (FR-007: sin subida a VT); regla de diseño: los `detalles` citan extensiones y tipos, no nombres de archivo completos (research D13) |
| V.5 | Adjuntos en memoria, sin ejecutar, con límites | PASS | Núcleo del FR-006: procesamiento solo en memoria con límites de entradas/bytes/relación; verificación doble en pruebas (AST del paquete + tmpdir que queda vacío: AC-ADJ-05) |
| V.6 | Sin archivos a terceros por defecto | PASS | FR-007: la política de subida a VT queda documentada como `VT_UPLOAD_UNKNOWN=false`; el código de VirusTotal pertenece a la spec 006 |
| V.7 | Uso permitido de APIs externas | N/A | La spec no realiza llamadas a APIs externas |
| V.8 | API con X-API-Key única, sin roles | N/A | Esta spec no expone endpoints |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-007; lectura de códigos QR, consulta a VirusTotal y análisis dinámico quedan fuera (Assumptions de la spec) |
| VI.2 | No inventar valores | PASS | 100 entradas / 100 MB / 100:1, los 9 códigos `ADJ_*`, severidades y puntos salen textualmente de FR-005 y del catálogo 5.3; las listas de extensiones son los defaults del M05, configurables vía env (research D8) |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Quedan `[VERIFICAR]`: API exacta de `VBA_Parser` con objetos file-like, excepciones reales de `pypdf` con PDFs malformados, cobertura real de `filetype` con formatos ambiguos (marcados en quickstart) |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.
**Re-evaluación post-fase 1**: sin cambios de alcance; D9 (sin wiring al pipeline),
D10 (sin cambios en `models.py`) y D5 (zip abortado por streaming con tope) confirman
los gates PASS sin bajar umbrales ni inventar valores.

## Project Structure

### Documentation (this feature)

```text
specs/005-analisis-adjuntos/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── adjuntos-api.md  # Phase 1 output (API pública del paquete adjuntos)
├── checklists/
│   └── requirements.md  # checklist de requirements (scaffolding de specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── models.py                    # SIN CAMBIOS (Adjunto ya trae nombre, tipo_declarado, tamano_bytes, sha256)
│   ├── agent.py                     # SIN CAMBIOS (el wiring lo hacen las specs 006/008 — D9)
│   ├── normalizacion/               # SIN CAMBIOS (sigue exponiendo EmailData con Adjunto: nombre, tipo, tamaño, sha256)
│   └── adjuntos/                    # NUEVO paquete (FR-001..FR-007)
│       ├── __init__.py              #   API pública: analizar_adjunto, AnalisisAdjunto, ConfigAdjuntos
│       ├── modelos.py               #   AnalisisAdjunto, catálogo 5.3 (código→severidad/puntos), constantes de bandera
│       ├── configuracion.py         #   ConfigAdjuntos desde env + ConfiguracionError (listas de extensión, límites zip)
│       ├── hashes.py                #   SHA-256 (principal) + MD5 + SHA-1 en memoria (FR-001)
│       ├── firma.py                 #   magic bytes (filetype) vs extensión y Content-Type → ADJ_TIPO_NO_COINCIDE (FR-002)
│       ├── extensiones.py           #   riesgo, doble extensión, HTML/SVG → ADJ_EXTENSION_RIESGO/ADJ_DOBLE_EXTENSION/ADJ_HTML (FR-003)
│       ├── office.py                #   Adapter olevba + relaciones OOXML externas → ADJ_MACRO/ADJ_ENLACE_EXTERNO (FR-004)
│       ├── pdf.py                   #   pypdf solo lectura + escaneo crudo → ADJ_PDF_ACTIVO (FR-004)
│       ├── comprimidos.py           #   zipfile con límites 100/100MB/100:1 y cifrado → ADJ_CIFRADO/ADJ_ARCHIVO_SOSPECHOSO (FR-005)
│       └── motor.py                 #   Registry de detectores puro y ordenado (orchestration)

tests/
├── unit/
│   ├── conftest.py                  # EDITAR: fixtures de adjuntos sintéticos en memoria
│   ├── vector_eicar.py              # NUEVO (helper, no prueba): generador EICAR en memoria + EICAR_SHA256 (AC-ADJ-02; lo reutiliza la spec 006)
│   ├── test_ac_adj_01_hashes.py     # NUEVO (AC-ADJ-01: SHA-256 vs referencia externa en 3 archivos)
│   ├── test_ac_adj_02_eicar.py      # NUEVO (AC-ADJ-02: EICAR reconocido por hash, generado en memoria)
│   ├── test_ac_adj_03_extension_tipo.py # NUEVO (AC-ADJ-03: factura.pdf.exe → DOBLE; exe→.pdf → TIPO_NO_COINCIDE)
│   ├── test_ac_adj_04_zip_bomb.py   # NUEVO (AC-ADJ-04: relaciones 99:1, 100:1 y 101:1)
│   ├── test_ac_adj_05_sin_escritura_ejecucion.py # NUEVO (AC-ADJ-05: AST del paquete + tmpdir vacío)
│   ├── test_ac_adj_06_entradas_hostiles.py # NUEVO (AC-ADJ-06: vacío, truncado, `..`, rutas + hypothesis)
│   ├── test_extensiones.py          # NUEVO (tabla de decisión extensión × familia × disposición)
│   ├── test_office.py               # NUEVO (OOXML con macro/enlace externo + doble de olevba)
│   ├── test_pdf.py                  # NUEVO (OpenAction/JavaScript/Launch, PDF truncado)
│   └── test_comprimidos.py          # NUEVO (cifrado, >100 entradas, >100 MB, ratio)
├── test_pipeline.py                 # SIN CAMBIOS (regresión: debe seguir verde)
└── fixtures/                        # SIN CAMBIOS (nada malicioso se guarda en el repo: SC-003)

scripts/
└── verify.py                        # EDITAR: lint/mypy/cobertura incluyen el paquete adjuntos
                                     # (extensión de compuertas sin bajar umbrales)

pyproject.toml               # EDITAR: mypy override estricto para adjuntos.*
requirements.txt             # EDITAR: filetype==1.2.0, oletools==0.60.2, pypdf==6.21.2 (deps fijadas)
.env.example                 # EDITAR: ADJ_EXTENSIONES_RIESGO, ADJ_EXTENSIONES_HTML,
                             # ADJ_EXTENSIONES_DOCUMENTO, ADJ_LIMITE_ENTRADAS_ZIP,
                             # ADJ_LIMITE_DESCOMPRIMIDO_ZIP, ADJ_RATIO_MAXIMO_ZIP,
                             # VT_UPLOAD_UNKNOWN=false (defaults del M05, sin secretos)
README.md                    # EDITAR: módulo M05 y comando de pruebas
AGENTS.md                    # EDITAR: nota del paquete adjuntos/ y de las 3 dependencias nuevas
```

**Structure Decision**: se conserva la estructura existente; el análisis de adjuntos
vive en un paquete nuevo dentro de `level2_agent/` porque consume el `Adjunto` de
`models.py` (spec 002) y las specs 006/008 lo consumirán desde ahí. Cada familia de
detección es un módulo de funciones/estrategias puras (Strategy + Registry + Adapter,
`research.md` D2/D3). El paquete **no** se conecta al pipeline en esta spec (D9): los
payloads viven solo durante la normalización y el wiring (llamar `analizar_adjunto`
por cada adjunto y acumular resultados) lo deciden las specs consumidoras. `models.py`
no cambia (D10): `AnalisisAdjunto` es un modelo propio del paquete, no un campo nuevo
de `EmailData`. Las compuertas de la spec 000 se EXTENDEN al paquete nuevo (mismo
mecanismo de las specs 002/003): sin eso el código nuevo quedaría sin medir y
violaría II.3/III.4.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS).
