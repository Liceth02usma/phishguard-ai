# Implementation Plan: Agente de IA Sin Estado

**Branch**: `feature/agente-ia-sin-estado` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-agente-ia-sin-estado/spec.md`

## Summary

Refactorizar el agente ReAct para que sea sin memoria, sin herramientas con efectos
externos, y resistente a inyección de instrucciones. El agente recibe evidencia
estructurada (banderas, auth, URLs, adjuntos, score, texto truncado dentro de
delimitadores `<correo>…</correo>`) y devuelve un JSON validado por esquema
Pydantic. La única herramienta es `busqueda_vectorial` (solo lectura). Se retiran
`check_ip_reputation` y `jira_integration` del agente. Tope diario de llamadas
(`LLM_MAX_DIARIO`); al superarlo, zona gris → `revision_manual`. Salida
invalidada → 1 reintento → `revision_manual`. El prompt declara que el contenido
del correo es dato no confiable.

## Technical Context

**Language/Version**: Python 3.10+ (3.11 en CI)

**Primary Dependencies**: LangChain/LangGraph (agente ReAct existente),
Google Generative AI (Gemini), MongoDB Atlas Vector Search (RAG),
Pydantic (validación de salida)

**Storage**: MongoDB `phishguard.docs_phishing` (RAG vector store);
contador diario en `phishguard.llm_contador` (TTL)

**Testing**: pytest + respuestas simuladas (AC-AGT-06: cero llamadas al modelo real);
fixtures de inyección en `tests/fixtures/inyeccion/`

**Target Platform**: Windows (desarrollo) / Linux (CI)

**Project Type**: library (módulo interno del pipeline)

**Performance Goals**: Tope diario configurable; límite de tokens por llamada

**Constraints**: AC-AGT-06 (sin llamadas al modelo real en pruebas);
AC-AGT-02 (resistencia a inyección); temperatura 0; salida validada por esquema

**Scale/Scope**: Refactor de `agent.py` + `prompts.py` + `tools/`; nuevo módulo
`src/level2_agent/agente/` (5 módulos); ~8 archivos de prueba; 6 ACs;
0 dependencias nuevas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Art. | Requisito | Estado | Evidencia |
|---|---|---|---|
| I.1–I.3 | Rama `feature/agente-ia-sin-estado` creada antes que artefactos | PASS | Setup script la crea |
| I.4–I.5 | Conventional Commits con AC | PASS | Flujo estándar |
| II.1 | Pruebas antes que código | PASS | TDD por AC |
| II.2 | ≥ 3 técnicas justificadas | PASS | Respuestas simuladas (AC-AGT-06), fixtures de inyección (AC-AGT-02), valores límite (tope N-1/N/N+1, AC-AGT-05) |
| II.3 | ≥ 80 % líneas y ramas | PASS | `--cov-branch --cov-fail-under=80` |
| II.4 | Sin pruebas sin assert | PASS | Cada prueba verifica herramienta/veredicto/esquema |
| II.5 | Sin red real ni hora sin controlar | PASS | AC-AGT-06: respuestas simuladas; reloj inyectado para contador diario |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-AGT-01..06")` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | Extensión aditiva |
| III.1 | Archivos ≤ 500 líneas | PASS | 5 módulos por responsabilidad; el mayor estimado < 300 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Entrada agrupada en `EntradaAgente` (Pydantic) |
| III.3 | snake_case español sin tildes | PASS | `consultar_agente`, `construir_prompt` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict`; `SalidaAgente` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Adapter (modelo intercambiable FR-008), Factory (prompt), Validator (salida) |
| III.6 | Sin números ni cadenas mágicos | PASS | `LLM_MAX_DIARIO`, delimitadores `<correo>`/`</correo>`, longitudes máximas como constantes |
| III.7 | Una responsabilidad por módulo | PASS | agente.py (orquestador), prompt.py (factory), validador.py (salida), contador.py (tope diario), modelos.py (tipos) |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | Sin deps nuevas |
| III.9 | Manejo de errores explícito | PASS | Salida invalidada → 1 reintento → `revision_manual`; tope superado → `revision_manual` sin llamada |
| IV.1 | Definición de terminado | PASS | `verify.py` exit 0 |
| V.1 | Fallar hacia revisar | PASS | Tope superado / salida invalidada → `revision_manual` |
| V.2 | Acciones por código determinista | PASS | El agente NO ejecuta acciones; su opinión alimenta al motor de decisión (spec 08) |
| V.3 | Secretos fuera de repo | PASS | `GOOGLE_API_KEY` en `.env`, gitignored |
| V.4 | PII enmascarada | PASS | `enmascarar_para_terceros` + delimitadores `<correo>` |
| V.5–V.7 | Adjuntos/SSRF/API externa | N/A | El agente no procesa adjuntos directamente ni llama APIs (solo RAG de solo lectura) |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..008; fuera: acciones Gmail/Jira (spec 10), elección del modelo |
| VI.2 | No inventar valores | PASS | Esquema de salida literal de M07; delimitadores `<correo>` de M07 |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | `[VERIFICAR]`: fuentes RAG existentes (FR-006), modelo final (FR-008) |
| VII.3 | Verificación de cumplimiento | PASS | Esta tabla + sección en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.

## Project Structure

### Documentation (this feature)

```text
specs/009-agente-ia-sin-estado/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── agente-ia.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/level2_agent/agente/
├── __init__.py           # API pública: consultar_agente, EntradaAgente, SalidaAgente
├── modelos.py            # EntradaAgente, SalidaAgente, ResultadoAgente
├── prompt.py             # Factory de prompts con delimitadores y declaración de seguridad
├── validador.py          # Validación de salida con esquema Pydantic + reintento
├── contador.py           # Contador diario de llamadas LLM (Mongo/in-memory)
└── agente.py             # Orquestador: construir prompt → llamar modelo → validar → resultado

tests/unit/
├── dobles_agente.py              # Simulador de modelo y RAG
├── test_ac_agt_01_herramientas.py # AC-AGT-01: herramientas = [busqueda_vectorial]
├── test_ac_agt_02_inyeccion.py   # AC-AGT-02: 10 fixtures de inyección
├── test_ac_agt_03_esquema.py     # AC-AGT-03: salida invalidada → reintento → revision_manual
├── test_ac_agt_04_regla_dura.py  # AC-AGT-04: agente no baja regla dura
├── test_ac_agt_05_tope.py        # AC-AGT-05: tope diario N-1/N/N+1
└── test_ac_agt_06_simuladas.py   # AC-AGT-06: cero llamadas al modelo real

tests/fixtures/inyeccion/          # 10 correos con instrucciones inyectadas
├── inyeccion_01.json
├── ...
└── inyeccion_10.json
```

**Structure Decision**: Paquete nuevo `src/level2_agent/agente/` (6 módulos),
siguiendo el patrón de `decision/`, `banderas/`, etc. El agente existente en
`agent.py` se refactoriza para delegar en este paquete. Las herramientas
`ip_reputation.py` y `jira_integration.py` se retiran del agente (Jira se
mantiene como función plain para la spec 010).

## Complexity Tracking

> Art. V.1 (fallar hacia revisar) justifica el reintento + revision_manual
> en caso de salida invalidada o tope superado.
