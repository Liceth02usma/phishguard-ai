# Feature Specification: Agente de IA Sin Estado

**Feature Branch**: `feature/agente-ia-sin-estado`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Un agente sin memoria y sin autonomía sobre efectos externos, que explique y desempate la zona gris con evidencia ya calculada."

## Context

**Problema**: el agente tiene herramientas con efectos (Jira) y consulta VirusTotal por su cuenta, recibe HTML crudo y su salida no está limitada; es vulnerable a inyección de instrucciones y a consumo sin límite.

**Objetivo**: un agente sin memoria y sin autonomía sobre efectos externos, que explique y desempate la zona gris con evidencia ya calculada.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M07.

**Depende de**: 01, 08.

## User Scenarios & Testing

### User Story 1 - Agente sin estado, sin efectos externos, resistente a inyección (Priority: P1)

El agente se invoca sin memoria, con una única herramienta de solo lectura (búsqueda vectorial). Recibe evidencia estructurada (banderas, SPF/DKIM/DMARC, URLs, adjuntos con reputación, score genético, texto limpio y truncado dentro de delimitadores) y devuelve un JSON validado por esquema. El prompt declara que el contenido del correo es dato no confiable. Tope diario de llamadas y límite de tokens; al superarlo, la zona gris va a `revision_manual`.

**Why this priority**: el agente actual es vulnerable a inyección de instrucciones (procesa texto de atacantes) y a consumo sin límite. Es un requisito de seguridad del Art. 0.6.

**Independent Test**: con respuestas simuladas, verificar que la lista de herramientas es `[busqueda_vectorial]`, que las instrucciones inyectadas no cambian el veredicto, y que al superar el tope diario la zona gris va a `revision_manual` sin llamar al modelo.

**Acceptance Scenarios**:

1. **AC-AGT-01**: la lista de herramientas del agente es exactamente `[busqueda_vectorial]`.
2. **AC-AGT-02**: con 10 correos con instrucciones para el modelo (en cuerpo, asunto, texto oculto y nombre del adjunto), el veredicto no cambia respecto al mismo correo sin esas frases.
3. **AC-AGT-03**: una salida que no cumple el esquema se reintenta 1 vez y, si persiste, produce `revision_manual`.
4. **AC-AGT-04**: el agente no puede cambiar a menor un veredicto de regla dura (verificado junto con la spec 08).
5. **AC-AGT-05**: al superar `LLM_MAX_DIARIO`, la zona gris va a `revision_manual` sin llamar al modelo (probar en N-1, N y N+1 llamadas).
6. **AC-AGT-06**: ninguna prueba llama al modelo real; se usan respuestas simuladas.

### Edge Cases

- Salida que no cumple el esquema (1 reintento, luego `revision_manual`).
- Tope diario en N-1, N, N+1 llamadas.
- Instrucciones inyectadas en cuerpo, asunto, texto oculto y nombre de adjunto.
- Consulta al RAG con texto del correo sin sanear.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Sin memoria (spec 01): cada invocación recibe solo la evidencia del correo actual.
- **FR-002** (RF2): Única herramienta: búsqueda vectorial de solo lectura. Se retiran del agente la herramienta de Jira y la de reputación de IP.
- **FR-003** (RF3): Entrada estructurada: banderas, estados SPF/DKIM/DMARC, URLs y adjuntos con su reputación, puntaje genético y el texto limpio y truncado del correo, dentro de delimitadores; el prompt declara que el contenido del correo son datos no confiables.
- **FR-004** (RF4): Salida validada con un esquema (resumen, análisis técnico, es_phishing, indicadores, nivel de severidad, justificación) con longitudes máximas y temperatura 0. Si no cumple, 1 reintento; si persiste, `revision_manual`.
- **FR-005** (RF5): La consulta al RAG nunca usa texto del correo sin sanear.
- **FR-006** (RF6): Fuentes del RAG versionadas con metadatos de fuente, versión y fecha; control de quién carga documentos. [VERIFICAR] cuántas fuentes existen hoy.
- **FR-007** (RF7): Tope diario de llamadas (`LLM_MAX_DIARIO`) y límite de tokens por llamada; al superarlo, la zona gris va a `revision_manual`.
- **FR-008** (RF8): El modelo se puede intercambiar por configuración (decisión pendiente del equipo).

## Success Criteria

### Measurable Outcomes

- **SC-001**: el agente no tiene herramientas con efectos externos.
- **SC-002**: las instrucciones inyectadas en el correo no cambian el veredicto.
- **SC-003**: al superar el tope diario, la zona gris va a `revision_manual` sin llamada al modelo.

## Assumptions

- **Fuera de alcance**: acciones en Gmail o Jira, y la elección final del modelo.
- **Hint para plan**: Adapter sobre el modelo, validación con Pydantic, Factory de prompts; fixtures de inyección en `tests/fixtures/inyeccion/` tratadas solo como datos (Artículo 0).
