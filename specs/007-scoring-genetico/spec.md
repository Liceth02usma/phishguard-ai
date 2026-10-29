# Feature Specification: Scoring con Clasificador Lineal y Banderas

**Feature Branch**: `feature/scoring-genetico`

**Created**: 2026-10-22

**Updated**: 2026-10-28 — reemplazo del algoritmo genético por clasificador lineal pre-entrenado

**Status**: Draft

**Input**: User description: "Un puntaje final reproducible que combine un clasificador lineal ya entrenado con las banderas, sin sesgos evidentes, con el modelo versionado y accesible para correos en español, gratuito y simple."

## Context

**Problema**: el algoritmo genético puntúa con pesos negativos para señales que suelen subir el riesgo (apelación al miedo, fecha límite, URL acortada) y un correo sin señales recibe 50 por la sigmoide. Además no combina las banderas deterministas. Los pesos están hardcoded sin procedimiento de entrenamiento formal.

**Objetivo**: un puntaje final reproducible que combine un clasificador lineal pre-entrenado (entrenado fuera de línea sobre el conjunto etiquetado) con las banderas deterministas, sin sesgos evidentes y con el modelo versionado. El clasificador usa las mismas 32 características de genes ya extraídas del correo, pero con coeficientes entrenados formalmente en vez de los pesos del AG.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M10.

**Depende de**: 03, 04, 05.

## User Scenarios & Testing

### User Story 1 - Score final que combina clasificador lineal + banderas (Priority: P1)

Se conservan las 32 características (genes) como entrada al clasificador. El clasificador lineal produce `score_clasificador = 100 × σ(Σ wᵢ·geneᵢ + b)` donde los coeficientes `w` y el intercepto `b` provienen de un modelo pre-entrenado almacenado en `clasificador_v1.json`. `score_final = min(100, score_clasificador + puntos_de_banderas)` con tope de 60 para banderas (que nunca reducen el puntaje). Un correo con 0 genes activos da `score_clasificador < 30` por diseño del entrenamiento. La coincidencia de palabras es por palabra completa. El modelo se versiona y cada análisis guarda la versión usada.

**Why this priority**: el score final es el insumo principal del motor de decisión (spec 08). Los sesgos actuales (pesos negativos, score 50 sin señales) producen falsos negativos.

**Independent Test**: dar un correo con genes y banderas conocidos y verificar `score_final`, la versión del modelo y que una bandera adicional no reduce el puntaje.

**Acceptance Scenarios**:

1. **AC-SCO-01**: un correo con 0 genes activos da `score_clasificador < 30`.
2. **AC-SCO-02**: activar una bandera adicional nunca reduce el puntaje (prueba basada en propiedades).
3. **AC-SCO-03**: cada análisis guarda `version_modelo`.
4. **AC-SCO-04**: con el conjunto de la spec 15, recall ≥ 95 % y falsos positivos ≤ 2 % (si no se cumple, se informa el resultado real sin ajustar umbrales por cuenta propia).
5. **AC-SCO-05**: valores límite del tope: banderas que suman 59, 60 y 61 puntos; `score_final` en 99, 100 y 101 antes de limitar.
6. **AC-SCO-06**: "urgente" no coincide dentro de "insurgente" ni se activa por subcadena.

### Edge Cases

- 0 genes activos.
- Banderas que suman 59, 60, 61 puntos.
- `score_final` 99, 100, 101 antes de `min(100, ...)`.
- Palabra clave como subcadena de otra.
- Archivo de modelo ausente o corrupto.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Conservar las 32 características (genes) como entrada al clasificador lineal. La extracción de genes permanece igual; solo cambia la función de puntuación.
- **FR-002** (RF2): `score_final = min(100, score_clasificador + puntos_de_banderas)`; los puntos de banderas suman con tope de 60; una bandera nunca reduce el puntaje.
- **FR-003** (RF3): Un correo con 0 genes activos produce `score_clasificador < 30` — garantizado por el entrenamiento del clasificador sobre el conjunto etiquetado.
- **FR-004** (RF4): Coincidencia de palabras por palabra completa, no por subcadena.
- **FR-005** (RF5): `dominio_externo` y `mismatch_dominio_url` usan listas de dominios propios y de proveedores de confianza.
- **FR-006** (RF6): El modelo se versiona (`clasificador_v1.json` con coeficientes, intercepto y metadata) y cada análisis guarda la versión usada.
- **FR-007** (RF7): Documentar el procedimiento de entrenamiento, el conjunto, los hiperparámetros y la fecha; revisar los coeficientes contra el conjunto etiquetado de la spec 15.

## Success Criteria

### Measurable Outcomes

- **SC-001**: un correo sin señales recibe `score_clasificador < 30` (no 50).
- **SC-002**: una bandera adicional nunca reduce el puntaje.
- **SC-003**: contra el conjunto etiquetado (spec 15), recall ≥ 95 % y falsos positivos ≤ 2 %.

## Assumptions

- **Clasificador pre-entrenado**: el modelo se entrena fuera de línea (en un notebook o script de entrenamiento, fuera del alcance de esta spec) sobre el conjunto etiquetado (`100correos.csv`, spec 15) y se exporta como JSON con los coeficientes y el intercepto. No se requiere scikit-learn en runtime — la predicción es un producto punto en Python puro.
- **Gratuito y simple**: cero dependencias nuevas para inferencia; el modelo es un archivo JSON versionado; el entrenamiento usa scikit-learn (ya disponible en el entorno de desarrollo).
- **Correos en español**: las 32 características ya manejan términos en español ("urgente", "banco", "verificar", "premio", etc.); el clasificador hereda esta cobertura.
- **Fuera de alcance**: reglas duras y veredicto (spec 08), reentrenamiento automático, entrenamiento del modelo (se hace previo a la implementación de esta spec).
- **Hint para plan**: modelo como datos versionados (JSON), función pura de puntuación; pruebas con `hypothesis` y con la tabla de valores límite.

## Clarifications

### Session 2026-10-28

- Q: ¿Reemplazar el algoritmo genético por un clasificador lineal pre-entrenado? → A: Sí — reemplazar el AG (32 pesos hardcoded + sigmoide) por un clasificador lineal cuyos coeficientes provienen de un modelo entrenado formalmente, exportado como JSON, sin dependencias nuevas en runtime. Las 32 características (genes) se conservan como entrada.
