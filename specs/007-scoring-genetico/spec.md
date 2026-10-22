# Feature Specification: Scoring Genético con Banderas

**Feature Branch**: `feature/scoring-genetico`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Un puntaje final reproducible que combine el algoritmo genético con las banderas, sin sesgos evidentes y con los pesos versionados."

## Context

**Problema**: el algoritmo genético puntúa con pesos negativos para señales que suelen subir el riesgo (apelación al miedo, fecha límite, URL acortada) y un correo sin señales recibe 50 por la sigmoide. Además no combina las banderas deterministas.

**Objetivo**: un puntaje final reproducible que combine el algoritmo genético con las banderas, sin sesgos evidentes y con los pesos versionados.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M10.

**Depende de**: 03, 04, 05.

## User Scenarios & Testing

### User Story 1 - Score final que combina genético + banderas (Priority: P1)

Se conservan los 32 genes y la sigmoide como señal heurística. `score_final = min(100, score_genetico + puntos_de_banderas)` con tope de 60 para banderas (que nunca reducen el puntaje). Un correo con 0 genes activos da `score_genetico < 30` por sesgo configurable. La coincidencia de palabras es por palabra completa. Los pesos se versionan (`pesos_v1.json`) y cada análisis guarda la versión usada.

**Why this priority**: el score final es el insumo principal del motor de decisión (spec 08). Los sesgos actuales (pesos negativos, score 50 sin señales) producen falsos negativos.

**Independent Test**: dar un correo con genes y banderas conocidos y verificar `score_final`, la versión de pesos y que una bandera adicional no reduce el puntaje.

**Acceptance Scenarios**:

1. **AC-SCO-01**: un correo con 0 genes activos da `score_genetico < 30`.
2. **AC-SCO-02**: activar una bandera adicional nunca reduce el puntaje (prueba basada en propiedades).
3. **AC-SCO-03**: cada análisis guarda `version_pesos`.
4. **AC-SCO-04**: con el conjunto de la spec 15, recall ≥ 95 % y falsos positivos ≤ 2 % (si no se cumple, se informa el resultado real sin ajustar umbrales por cuenta propia).
5. **AC-SCO-05**: valores límite del tope: banderas que suman 59, 60 y 61 puntos; `score_final` en 99, 100 y 101 antes de limitar.
6. **AC-SCO-06**: "urgente" no coincide dentro de "insurgente" ni se activa por subcadena.

### Edge Cases

- 0 genes activos.
- Banderas que suman 59, 60, 61 puntos.
- `score_final` 99, 100, 101 antes de `min(100, ...)`.
- Palabra clave como subcadena de otra.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Conservar los 32 genes y la sigmoide como señal heurística. [VERIFICAR] los pesos y el sesgo actuales.
- **FR-002** (RF2): `score_final = min(100, score_genetico + puntos_de_banderas)`; los puntos de banderas suman con tope de 60; una bandera nunca reduce el puntaje.
- **FR-003** (RF3): Un correo con 0 genes activos produce `score_genetico < 30` mediante un sesgo configurable.
- **FR-004** (RF4): Coincidencia de palabras por palabra completa, no por subcadena.
- **FR-005** (RF5): `dominio_externo` y `mismatch_dominio_url` usan listas de dominios propios y de proveedores de confianza.
- **FR-006** (RF6): Los pesos se versionan (`pesos_v1.json`) y cada análisis guarda la versión usada.
- **FR-007** (RF7): Documentar el conjunto de entrenamiento, la semilla y la fecha, y revisar los pesos negativos contra el conjunto etiquetado de la spec 15.

## Success Criteria

### Measurable Outcomes

- **SC-001**: un correo sin señales recibe `score_genetico < 30` (no 50).
- **SC-002**: una bandera adicional nunca reduce el puntaje.
- **SC-003**: contra el conjunto etiquetado (spec 15), recall ≥ 95 % y falsos positivos ≤ 2 %.

## Assumptions

- **Fuera de alcance**: reglas duras y veredicto (spec 08), reentrenamiento automático.
- **Hint para plan**: pesos como datos versionados, función pura de puntuación; pruebas con `hypothesis` y con la tabla de valores límite.
