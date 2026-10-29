# Implementation Plan: Motor de Decisión Determinista

**Branch**: `feature/motor-decision` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-motor-decision/spec.md`

## Summary

Construir un motor de decisión determinista y explicable en `src/level2_agent/decision/`
(5 módulos) que aplique primero reglas duras R1–R5 (la primera que aplica fija
`malicioso`), luego una tabla ordenada que combina `score_final`, la confirmación
del agente y las verificaciones incompletas para producir `VeredictoMotor` con
`veredicto`, `score_final`, `nivel_severidad`, `ruta`, `reglas_aplicadas`,
`banderas` y `verificaciones_incompletas`. El motor es una **función pura** que
no llama servicios externos; toda la información le llega como parámetros
inyectados. La palabra "seguro" jamás aparece en la salida (FR-006, Art. V.1).

## Technical Context

**Language/Version**: Python 3.10+ (3.11 en CI)

**Primary Dependencies**: Pydantic (modelos de entrada/salida); sin dependencias
nuevas — consume tipos de las specs 003–007 vía import

**Storage**: N/A — el motor es stateless; la persistencia del resultado es
responsabilidad de la spec 011

**Testing**: pytest + hypothesis (propiedad: determinismo); tabla de decisión
como estructura de datos testeable; valores límite (29/30/75-75/76)

**Target Platform**: Windows (desarrollo) / Linux (CI) — Python puro, sin
diferencias

**Project Type**: library (módulo interno del pipeline, sin endpoints HTTP)

**Performance Goals**: < 1 ms por correo (función pura, sin I/O)

**Constraints**: 100 % cobertura de ramas (AC-DEC-06); función pura
(determinismo AC-DEC-04); sin I/O; sin llamadas al agente (spec 09 lo invoca,
no este motor)

**Scale/Scope**: 5 módulos en `src/level2_agent/decision/`, ~8 archivos de
prueba en `tests/unit/`, 5 reglas duras + 6 filas de tabla, 7 ACs; 0
dependencias nuevas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Art. | Requisito | Estado | Evidencia |
|---|---|---|---|
| I.1–I.3 | Rama `feature/motor-decision` creada antes que artefactos | PASS | Setup script la crea |
| I.4–I.5 | Sin commits en main; Conventional Commits con AC | PASS | Flujo estándar |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | TDD por AC |
| II.2 | ≥ 3 técnicas justificadas | PASS | Valores límite (obligatorio: 29/30/75/76), tabla de decisión (obligatorio: FR-002), pruebas basadas en propiedades (determinismo AC-DEC-04), integración con dobles (VT caído AC-DEC-03) |
| II.3 | ≥ 80 % líneas y ramas; 100 % ramas del motor (AC-DEC-06) | PASS | `--cov-branch --cov-fail-under=80` + gate extra 100 % ramas en `motor.py` |
| II.4 | Sin pruebas sin assert | PASS | Cada prueba verifica veredicto/severidad/ruta |
| II.5 | Sin red real ni hora sin controlar | PASS | Función pura: cero I/O |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-DEC-01..07")` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | Extensión aditiva |
| III.1 | Archivos ≤ 500 líneas | PASS | 5 módulos por responsabilidad; el mayor estimado < 200 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Entrada agrupada en `EntradaMotor` (Pydantic); la función principal tiene 1 parámetro |
| III.3 | snake_case español sin tildes | PASS | `evaluar_veredicto`, `reglas_duras`, `tabla_decision` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict`; `VeredictoMotor` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Chain of Responsibility (reglas duras), tabla de decisión (FR-002) — nombrados en spec |
| III.6 | Sin números ni cadenas mágicas | PASS | Umbrales 30/76 como constantes nombradas; códigos de regla R1–R5 del catálogo |
| III.7 | Una responsabilidad por módulo | PASS | reglas.py (R1–R5), tabla.py (tabla FR-002), motor.py (orquestador), modelos.py (tipos) |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | Sin deps nuevas |
| III.9 | Manejo de errores explícito | PASS | El motor no lanza: toda entrada produce `VeredictoMotor` |
| IV.1 | Definición de terminado | PASS | `verify.py` exit 0 |
| V.1 | Fallar hacia revisar | PASS | Verificación incompleta → `revision_manual`, nunca `sin_indicadores` (FR-003, AC-DEC-03) |
| V.2 | Acciones por código determinista | PASS | El motor es código determinista; no invoca al agente (opinión llega como parámetro) |
| V.3 | Secretos fuera de repo | PASS | Sin secretos en este módulo |
| V.4 | PII enmascarada | PASS | El motor no persiste ni envía datos |
| V.5 | Adjuntos en memoria; SSRF2F validado | N/A | El motor no procesa adjuntos directamente |
| V.6 | Sin envío de archivos | N/A | El motor no envía archivos |
| V.7 | Uso permitido de API externa | N/A | El motor no llama APIs |
| VI.1 | Solo lo que pide la spec | PASS | Alcance =9 = FR-001..006; fuera: invocar agente (009), ejecutar acciones (010), persistir (011) |
| VI.2 | No inventar valores | PASS | Umbrales 30/76, severidades y reglas R1–R5 literales de M09; tabla literal de M09 |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | `[VERIFICAR]`: comportamiento real del agente (spec 09), interacción end-to-end con VT real |
| VII.3 | Verificación de cumplimiento | PASS | Esta tabla + sección en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.

## Project Structure

### Documentation (this feature)

```text
specs/008-motor-decision/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── motor-decision.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/level2_agent/decision/
├── __init__.py           # API pública: evaluar_veredicto, VeredictoMotor, EntradaMotor
├── modelos.py            # VeredictoMotor, EntradaMotor, ReglaDura, VerificacionIncompleta
├── reglas.py             # R1–R5: evaluación de reglas duras (Chain of Responsibility)
├── tabla.py              # Tabla de decisión FR-002 (6 filas, función pura)
└── motor.py              # Orquestador: reglas → tabla → VeredictoMotor

tests/unit/
├── test_ac_dec_01_reglas.py       # AC-DEC-01: cada R1–R5 se activa y no se activa
├── test_ac_dec_02_tabla.py        # AC-DEC-02: límites 29/30/75/76 ± agente
├── test_ac_dec_03_incompleta.py   # AC-DEC-03: VT caído → revision_manual
├── test_ac_dec_04_determinismo.py # AC-DEC-04: propiedad hypothesis ×10
├── test_ac_dec_05_sin_seguro.py   # AC-DEC-05: "seguro" no aparece
├── test_ac_dec_06_cobertura.py    # AC-DEC-06: 100 % ramas del motor
├── test_ac_dec_07_agente_no_baja.py # AC-DEC-07: regla dura + agente en contra
└── test_motor.py                  # Pruebas integradas del orquestador
```

**Structure Decision**: Paquete nuevo `src/level2_agent/decision/` (5 módulos),
siguiendo el patrón de `banderas/`, `analisis_urls/`, `adjuntos/`, `virustotal/`.
Importado como `src.level2_agent.decision`. Sin `__init__.py` en `src/` (igual
que specs anteriores). El motor es **intencionalmente NO wired** en `agent.py`
ni el poller — las specs 009/010 lo consumirán.

## Complexity Tracking

> Sin violaciones constitucionales que justificar.
