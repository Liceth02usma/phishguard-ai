# Feature Specification: Persistencia y Métricas de Análisis

**Feature Branch**: `feature/persistencia-metricas`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Guardar cada análisis de forma segura, con retención definida, y calcular las métricas del tablero."

## Context

**Problema**: no existe historial de análisis ni métricas; no se puede demostrar el recall ni los falsos positivos, y el frontend no tiene datos.

**Objetivo**: guardar cada análisis de forma segura, con retención definida, y calcular las métricas del tablero.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M14 (14.1 y 14.2) y las fórmulas de métricas de la especificación del frontend.

**Depende de**: 08.

## User Scenarios & Testing

### User Story 1 - Persistencia segura y métricas del tablero (Priority: P1)

Cada análisis se guarda en MongoDB con retención por TTL, sin HTML original ni contenido de adjuntos, con el correo enmascarado y el resultado completo. Las métricas (total, por veredicto, % sin modelo, duración media, por día en America/Bogota, indicadores frecuentes, tasa de falsos positivos, consultas VT y aciertos de caché) se calculan sobre los datos. Hay datos de siembra deterministas (100 análisis) y borrado de un análisis y su caché.

**Why this priority**: sin persistencia no hay métricas ni historial; el frontend (spec 12) no tiene datos y no se puede demostrar recall/falsos positivos (spec 15).

**Independent Test**: sembrar los 100 análisis, calcular métricas y verificar total 100, 55/15/30 por veredicto y 60 % sin modelo; borrar uno y verificar que desaparece con su caché.

**Acceptance Scenarios**:

1. **AC-PER-01**: un análisis guardado no contiene HTML original, adjuntos ni correos sin enmascarar.
2. **AC-PER-02**: los índices TTL existen con las retenciones indicadas.
3. **AC-PER-03**: las métricas sobre los datos de siembra dan exactamente total 100; 55/15/30 por veredicto y 60,0 % sin modelo.
4. **AC-PER-04**: `por_dia` tiene un elemento por cada día del rango, incluidos los de cero (probar 7, 30 y 90 días y el cambio de zona horaria).
5. **AC-PER-05**: la tasa de falsos positivos es nula (sin dato) cuando no hay retroalimentación, y correcta cuando la hay.
6. **AC-PER-06**: ejecutar la siembra dos veces deja exactamente 100 documentos de origen siembra y no toca los de usuario.
7. **AC-PER-07**: borrar un análisis elimina el documento y su caché asociada.

### Edge Cases

- Rango de 7, 30, 90 días con días en cero.
- Cambio de zona horaria (America/Bogota).
- Siembra ejecutada dos veces.
- Sin retroalimentación (tasa de FP nula).

## Requirements

### Functional Requirements

- **FR-001** (RF1): Colecciones: `analyses` (retención 90 días por índice TTL), `vt_cache` (TTL propio), `vt_cuota` (2 días), `procesados` (90 días) y `analyses_fallidos` (30 días). No existe colección de historial de chat.
- **FR-002** (RF2): El documento de análisis incluye origen, modo, fecha, duración, correo enmascarado, resultado completo (score, ruta, veredicto, severidad, banderas, reglas aplicadas, autenticación, URLs, adjuntos, versión de pesos y de modelo), acción y retroalimentación. NO se persiste HTML original ni contenido de adjuntos.
- **FR-003** (RF3): Índices por fecha y por veredicto; creados al iniciar si no existen.
- **FR-004** (RF4): Métricas: total, por veredicto, porcentaje resuelto sin modelo, duración media, por día (incluidos días en cero, zona America/Bogota), indicadores más frecuentes y tasa de falsos positivos; además consultas a VirusTotal y aciertos de caché.
- **FR-005** (RF5): Borrado a solicitud de un análisis y de su caché asociada.
- **FR-006** (RF6): Datos de siembra deterministas: 100 análisis (55 sin_indicadores, 15 sospechosos, 30 maliciosos; 60 por heurística y 40 con IA) generados por fórmula sin aleatoriedad.

### Key Entities

- **Analisis**: documento persistido con origen, modo, fecha, duración, correo enmascarado, resultado completo, acción y retroalimentación. Retención 90 días.
- **Metricas**: agregaciones (total, por veredicto, % sin modelo, duración media, por día, indicadores frecuentes, tasa de FP, consultas VT, aciertos de caché).

## Success Criteria

### Measurable Outcomes

- **SC-001**: los datos de siembra producen métricas exactas (total 100; 55/15/30; 60 % sin modelo).
- **SC-002**: `por_dia` cubre todos los días del rango incluidos los de cero.
- **SC-003**: ningún análisis persistido contiene HTML original, adjuntos o correos sin enmascarar.

## Assumptions

- **Fuera de alcance**: endpoints HTTP (spec 12).
- **Hint para plan**: Repository sobre MongoDB con una base de pruebas en memoria o contenedor local; agregaciones probadas con datos fijos.
