# Feature Specification: Eliminar Memoria Conversacional del Agente

**Feature Branch**: `refactor/eliminar-memoria`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Que el análisis de cada correo sea independiente de cualquier otro, y que no exista memoria conversacional en el sistema."

## Context

**Problema**: el agente guarda historial de chat en MongoDB (`memory.py`). Esto arrastra contexto entre correos, persiste datos de correos sin necesidad y permite que un correo influya en el análisis de los siguientes.

**Objetivo**: que el análisis de cada correo sea independiente de cualquier otro, y que no exista memoria conversacional en el sistema.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M01.

**Depende de**: 00 (calidad-base).

## User Scenarios & Testing

### User Story 1 - Análisis independiente por correo (Priority: P1)

Cada correo se analiza solo con su propia evidencia, sin que correos previos influyan en el resultado. La memoria conversacional y las colecciones de historial de chat dejan de existir.

**Why this priority**: la memoria compartida es un vector de contaminación entre correos (un correo podría alterar el análisis del siguiente). Es un requisito de seguridad/correctitud.

**Independent Test**: analizar el mismo conjunto de correos en dos órdenes distintos y verificar resultados idénticos por correo.

**Acceptance Scenarios**:

1. **AC-MEM-01**: ninguna ruta de código importa o escribe historial de chat (comprobación automática sobre el código).
2. **AC-MEM-02**: analizar 5 correos en dos órdenes distintos produce, para cada correo, el mismo score, veredicto y banderas.
3. **AC-MEM-03**: tras ejecutar el script de migración, las colecciones de historial no existen; ejecutarlo en modo simulación no borra nada.
4. **AC-MEM-04**: la colección del RAG conserva todos sus documentos tras la migración.

### Edge Cases

- Base sin colecciones de historial: el script termina sin error.
- Colección con millones de documentos: borrado por lotes.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Eliminar el módulo de memoria y toda importación, instancia, identificador de sesión y escritura de historial en el agente y el resto del código.
- **FR-002** (RF2): El agente se invoca sin estado: recibe solo la evidencia del correo actual.
- **FR-003** (RF3): Un script de una sola ejecución, con modo de simulación y confirmación explícita, elimina las colecciones de historial de chat de MongoDB Atlas.
- **FR-004** (RF4): Quitar de la configuración y del README cualquier variable o texto de memoria.
- **FR-005** (RF5): La base de conocimiento vectorial (RAG) NO se toca.

## Success Criteria

### Measurable Outcomes

- **SC-001**: el resultado de analizar un correo no depende de qué correos se analizaron antes.
- **SC-002**: tras la migración, no quedan colecciones de historial de chat en MongoDB y el RAG está intacto.

## Assumptions

- **Fuera de alcance**: cambios al prompt, a las herramientas del agente o al modelo.
- **Hint para plan**: eliminación y script de migración; prueba de independencia con dobles del modelo (respuestas deterministas).
