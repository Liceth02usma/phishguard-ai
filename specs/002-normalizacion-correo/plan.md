# Implementation Plan: Normalización y Saneado de Correo

**Branch**: `feature/normalizacion-correo` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-normalizacion-correo/spec.md`

## Summary

Construir un paquete de normalización `src/level2_agent/normalizacion/` que convierta
cualquier entrada (bytes crudos de Gmail, archivo `.eml` o payload JSON de la futura API)
en un `EmailData` ampliado, único, acotado y saneado: parseo MIME con `email.policy.default`,
cabeceras como lista ordenada de pares (conservando repetidas), HTML→texto con `HTMLParser`
de la estándar (sin scripts/estilos/comentarios/texto oculto, con texto de enlaces),
extracción de URLs y adjuntos (SHA-256 en memoria), cinco límites duros que activan la
bandera `LIMITE_EXCEDIDO` y revisión manual, y enmascarado de PII (Art. V.4) aplicado en la
vista que se envía al modelo de lenguaje. Se amplía `EmailData` sin romper el pipeline
existente (los consumidores actuales migran en specs 003–05), se integra el poller de Gmail
al normalizador y se extienden las compuertas de calidad (ruff/mypy/cobertura de `verify.py`)
al paquete nuevo sin bajar ningún umbral. TDD con rojo confirmado, `hypothesis` para
propiedades del enmascarado y trazabilidad AC-NORM-01..06.

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10)

**Primary Dependencies**: stdlib `email` (policy default), `html.parser`, `hashlib`,
`re`, Pydantic; nueva dependencia de prueba: `hypothesis` (fijada en `requirements.txt`,
sugerida por la spec); tooling: pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks

**Storage**: N/A — la persistencia de análisis llega en spec 11 (M14); esta spec define la
vista enmascarada que aquella usará y marca `htmlBody` como excluido de serialización

**Testing**: pytest con `@pytest.mark.ac("AC-NORM-NN")`, `hypothesis` (propiedades del
enmascarado), dobles (servicio Gmail falso), `--cov --cov-branch` sobre `scripts/` y el
paquete nuevo; ruff y `mypy --strict` sobre `scripts/`, `tests/unit/` y el paquete nuevo

**Target Platform**: Windows local + Linux CI (GitHub Actions `verify.yml`)

**Project Type**: librería dentro de `src/` (paquete `normalizacion`) integrada al poller

**Performance Goals**: parseo y saneado en memoria, sin escrituras a disco; límite duro de
25 MB de entrada

**Constraints**: pruebas deterministas sin red (Art. II.5); ningún `.py` > 500 líneas
(objetivo 300); funciones ≤ 40 líneas; `mypy --strict` sobre el código nuevo (Art. III.4)

**Scale/Scope**: ~5 módulos nuevos en `src/level2_agent/normalizacion/`, ~8 líneas de
integración en `gmail_poller.py`, 1 submodelo + campos en `models.py`, 2 líneas en
`agent.py` (vista enmascarada al LLM), ~7 archivos de prueba nuevos, 1 cambio de
compuertas en `verify.py` + `pyproject.toml`. Nada fuera de `specs/002-normalizacion-correo/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS | `feature/normalizacion-correo` (creada desde `main` antes de escribir nada; cumple regex Art. I.2) |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | commits `feat|test|chore: ... (AC-NORM-NN)` en la rama |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase de pruebas TDD dedicada en tasks.md; rojo verificado contra el código actual (modelos sin campos, paquete inexistente) |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 6 técnicas justificadas en `research.md` (D11): valores límite (obligatorio: 5 umbrales + dígitos 12/13/19/20), tabla de decisión (obligatorio: límites y entradas degradadas), partición de equivalencia (orígenes/formatos), propiedades con `hypothesis` (AC-NORM-04, hint de la spec), integración con dobles (poller), regresión (pipeline existente intacto) |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | `verify.py` y `pyproject.toml` se EXTENDEN para medir `src/level2_agent/normalizacion/` y `models.py` (ampliación de alcance, no bajada de umbral); el código nuevo es funcional y se prueba completo |
| II.4 | Sin pruebas sin `assert` | PASS | Toda prueba verifica comportamiento observable (campos, banderas, flags, texto resultante) |
| II.5 | Sin red real en pruebas | PASS | Parseo de `.eml`/bytes locales; poller probado con servicio Gmail falso; sin LLM real (fixtures de agente) |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-NORM-01..06")`; verificado con `scripts/check_trazabilidad_ac.py --spec specs/002-normalizacion-correo/spec.md` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica ninguna prueba existente para hacer pasar la spec; `fail_under` no baja (la media combinada sube) |
| III.1 | Archivos `.py` ≤ 500 líneas (objetivo 300) | PASS | Paquete dividido en 5 módulos por responsabilidad; estimado cada uno < 200 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Funciones puras pequeñas por etapa; el orquestador recibe un `CorreoBruto` |
| III.3 | `snake_case` en español sin tildes | PASS | `normalizar_desde_gmail`, `html_a_texto`, `enmascarar_para_terceros`, `LIMITE_URLS` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict` ampliado al paquete nuevo y a `models.py`; `Cabecera`/`Adjunto`/`EmailData` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Pipeline (etapas puras: parseo → HTML→texto → extracciones → límites → enmascarado) y Adapter (Gmail/`.eml`/API → `CorreoBruto`); nada más |
| III.6 | Sin números ni cadenas mágicas | PASS | `LIMITE_BYTES_CORREO`, `LIMITE_CARACTERES_TEXTO`, `LIMITE_URLS`, `LIMITE_ADJUNTOS`, `LIMITE_NIVELES_MIME`, `BANDERA_LIMITE_EXCEDIDO`, `BANDERA_ENTRADA_DEGRADADA` como constantes |
| III.7 | Una responsabilidad por módulo | PASS | Un módulo por etapa; el enmascarado es puro y reutilizable por la spec 11 |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | `hypothesis` con versión fija exacta al agregarse; ruff/mypy sobre el paquete nuevo |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` desnudo: cada parte degrada con bandera `ENTRADA_DEGRADADA`; excepción propia `NormalizacionError` documentada en el contrato |
| IV.1a–i | Definición de terminado | PASS | verify.py exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar | PASS | Límite excedido o entrada degradada → `revision_manual=True`; jamás "sin indicadores" por esta ruta |
| V.2 | DRY_RUN por defecto | PASS | Esta spec no ejecuta acciones externas; la integración del poller solo cambia la construcción del objeto |
| V.3 | Secretos fuera de reposo | PASS | Sin claves nuevas; no se leen `.env` ni credenciales en pruebas |
| V.4 | PII enmascarada antes de persistir/enviar a terceros | PASS | `enmascarar_para_terceros()` se aplica en `agent.py` antes de armar el prompt del LLM; `htmlBody` excluido de serialización (`Field(exclude=True)`) |
| V.5 | Adjuntos en memoria, sin ejecutar, con límites | PASS | SHA-256 con `hashlib` sobre bytes en memoria; nunca se escriben ni ejecutan; ≤ 20 adjuntos |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-006; el análisis de contenido/URLs/adjuntos (specs 003–06) queda fuera |
| VI.2 | No inventar valores | PASS | Los 5 umbrales y la regla de enmascarado salen textualmente de la spec; `MB = 1024²` y la bandera `ENTRADA_DEGRADADA` son decisiones de diseño documentadas en `research.md` (D6, D9), no reglas de dominio |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Campos actuales de `EmailData` VERIFICADOS en `models.py`; quedan `[VERIFICAR]`: contrato exacto del payload de la API (spec 12), integración con Gmail real y con credenciales reales |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.
**Re-evaluación post-fase 1**: sin cambios de alcance; D4 (compatibilidad de `EmailData`)
y D10 (extensión de compuertas) confirman los gates PASS sin bajar umbrales.

## Project Structure

### Documentation (this feature)

```text
specs/002-normalizacion-correo/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── normalizacion-api.md   # Phase 1 output (API pública del normalizador)
├── checklists/
│   └── requirements.md  # checklist de requirements (scaffolding de specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── models.py                    # EDITAR: EmailData ampliado (FR-001) + Cabecera, Adjunto
│   ├── agent.py                     # EDITAR (2 líneas): prompt con vista enmascarada (AC-NORM-04, V.4)
│   ├── normalizacion/               # NUEVO paquete (FR-001..FR-005)
│   │   ├── __init__.py              #   API pública: normalizar_desde_*, enmascarar_para_terceros
│   │   ├── parseo_mime.py           #   MIME/.eml/payload → CorreoBruto (FR-002, límite MIME)
│   │   ├── html_a_texto.py          #   HTMLParser: scripts/estilos/comentarios/ocultos fuera (FR-003)
│   │   ├── extraccion.py            #   URLs (href/src/action/texto) y adjuntos con SHA-256 (FR-001)
│   │   ├── limites.py               #   5 constantes + evaluación → LIMITE_EXCEDIDO (FR-004)
│   │   └── enmascarado.py           #   correos y dígitos 13–19 → vistas seguras (FR-005)
│   └── prompts.py                   # SIN CAMBIOS (recibe las mismas claves)
├── gmail_integration/
│   ├── gmail_poller.py              # EDITAR: procesar raw bytes con normalizar_desde_gmail
│   ├── gmail_reader.py              # EDITAR (mínimo): exponer get_message_raw (bytes)
│   └── email_to_emaildata.py        # SIN CAMBIOS (legacy, migrado en specs posteriores)
└── level3_logic/                    # SIN CAMBIOS (sigue leyendo los campos legacy)

tests/
├── unit/
│   ├── conftest.py                  # EDITAR: fixtures de correos normalizados/`.eml`
│   ├── test_ac_norm_01_cabeceras.py           # NUEVO (AC-NORM-01)
│   ├── test_ac_norm_02_html_texto.py          # NUEVO (AC-NORM-02)
│   ├── test_ac_norm_03_limites.py             # NUEVO (AC-NORM-03)
│   ├── test_ac_norm_04_enmascarado.py         # NUEVO (AC-NORM-04, con hypothesis)
│   ├── test_ac_norm_05_formato_email.py       # NUEVO (AC-NORM-05)
│   ├── test_ac_norm_06_entradas_degradadas.py # NUEVO (AC-NORM-06)
│   └── test_integracion_poller.py             # NUEVO (doble de servicio Gmail)
├── test_pipeline.py                 # SIN CAMBIOS (regresión: debe seguir verde)
└── fixtures/                        # SIN CAMBIOS

scripts/
└── verify.py                        # EDITAR: lint/mypy/cobertura incluyen el paquete nuevo
                                     # y models.py (D10 — ampliación de alcance, sin bajar umbrales)

pyproject.toml               # EDITAR: mypy override estricto para normalizacion.* y models
requirements.txt             # EDITAR: hypothesis con versión fija (dependencia de prueba)
README.md                    # EDITAR: describir la normalización y el comando de pruebas
AGENTS.md                    # EDITAR: nota del paquete normalizacion/ y hypothesis
```

**Structure Decision**: se conserva la estructura existente; el normalizador es un paquete
nuevo dentro de `level2_agent/` porque `EmailData` vive en `models.py` de ese paquete y las
specs 003–05 consumirán los resultados desde ahí. Cada etapa del pipeline es un módulo puro
(Pipeline + Adapter, `research.md` D1/D5). Las compuertas de la spec 000 se EXTENDEN al
paquete nuevo (D10): sin eso, el código nuevo quedaría sin medir y violaría II.3/III.4.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS).
