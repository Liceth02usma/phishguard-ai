# Feature Specification: Resiliencia del Poller de Gmail

**Feature Branch**: `feature/resiliencia-poller`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Procesar todos los correos pendientes de forma concurrente, idempotente y con degradación controlada."

## Context

**Problema**: el poller procesa un máximo de 5 correos por ciclo en un solo proceso, sin reintentos ni cola de fallidos; en una campaña masiva los correos se acumulan o se pierden.

**Objetivo**: procesar todos los correos pendientes de forma concurrente, idempotente y con degradación controlada.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M12.

**Depende de**: 10, 11.

## User Scenarios & Testing

### User Story 1 - Poller concurrente, idempotente y con degradación (Priority: P1)

Una cola con trabajadores concurrentes (4 por defecto) procesa todos los correos no leídos pendientes sin tope por ciclo, con idempotencia por identificador de mensaje, hasta 3 reintentos con espera exponencial (luego a `analyses_fallidos`), tiempos máximos por etapa (análisis 60 s, VT 10 s, URL 5 s, agente 30 s), una matriz de degradación ante caídas de servicios, apagado ordenado y estado disponible para la API.

**Why this priority**: en una campaña masiva el poller actual se satura o pierde correos. La resiliencia es operacionalmente crítica.

**Independent Test**: con VT y modelo simulados, inyectar 50 correos simultáneos y verificar que todos se procesan sin pérdida; simular cada fila de la matriz de degradación y verificar el comportamiento.

**Acceptance Scenarios**:

1. **AC-RES-01**: 50 correos simultáneos se procesan completos y sin pérdida (VirusTotal y modelo simulados).
2. **AC-RES-02**: un correo que falla 3 veces termina en `analyses_fallidos` con motivo y no bloquea a los demás.
3. **AC-RES-03**: cada fila de la matriz de degradación tiene una prueba que simula la caída y verifica el comportamiento.
4. **AC-RES-04**: un análisis de más de 60 s termina como `revision_manual` con `TIEMPO_AGOTADO` (probar 59, 60 y 61 s).
5. **AC-RES-05**: una señal de apagado deja terminar el análisis en curso y no inicia nuevos.
6. **AC-RES-06**: dos trabajadores que reciben el mismo mensaje lo procesan una sola vez.

### Edge Cases

- 50 correos simultáneos.
- Correo que falla 1, 2, 3 veces.
- Análisis de 59, 60, 61 s.
- Caída de VT, modelo, caché, RDAP, Gmail (matriz de degradación).
- Dos trabajadores con el mismo mensaje.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Cola de trabajo con trabajadores concurrentes (configurable, por defecto 4) que procesa todos los correos no leídos pendientes, sin tope fijo por ciclo.
- **FR-002** (RF2): Idempotencia por identificador del mensaje.
- **FR-003** (RF3): Hasta 3 reintentos por correo con espera exponencial; luego a `analyses_fallidos` con el motivo, sin bloquear a los demás.
- **FR-004** (RF4): Tiempos máximos: análisis completo 60 s; VirusTotal 10 s; expansión de URL 5 s; agente 30 s. Un análisis que excede 60 s termina como `revision_manual` con motivo `TIEMPO_AGOTADO`.
- **FR-005** (RF5): Matriz de degradación: VirusTotal caído sigue el análisis con `VT_NO_DISPONIBLE`; modelo caído lleva la zona gris a `revision_manual`; caché caída consulta sin caché; RDAP caído registra bandera sin penalizar; Gmail caído reintenta y alerta.
- **FR-006** (RF6): Apagado ordenado: termina el análisis en curso.
- **FR-007** (RF7): Estado del poller disponible para la API (último ciclo, pendientes, fallidos).

## Success Criteria

### Measurable Outcomes

- **SC-001**: 50 correos simultáneos se procesan completos sin pérdida.
- **SC-002**: cada caída de la matriz de degradación produce el comportamiento definido, sin pérdida ni bucle.
- **SC-003**: un análisis que excede 60 s termina como `revision_manual` con `TIEMPO_AGOTADO`.

## Assumptions

- **Fuera de alcance**: cambio de proveedor de colas externas (se usa concurrencia en el proceso).
- **Hint para plan**: `asyncio` con semáforo, Pipeline con tiempos máximos por etapa, relojes inyectables para pruebas de tiempo sin esperar.
