# Feature Specification: Acciones Idempotentes en Gmail y Jira

**Feature Branch**: `feature/acciones-gmail-jira`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Acciones idempotentes, deterministas y auditables, ejecutadas por código tras el veredicto final."

## Context

**Problema**: las acciones sobre Gmail y Jira se deciden por el resultado del modelo, pueden repetirse, no tienen modo de simulación y marcan como leído correo que no fue verificado.

**Objetivo**: acciones idempotentes, deterministas y auditables, ejecutadas por código tras el veredicto final.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M08.

**Depende de**: 08.

## User Scenarios & Testing

### User Story 1 - Acciones por veredicto, idempotentes y en simulacro (Priority: P1)

Tras el veredicto final, código determinista ejecuta acciones sobre Gmail y Jira según una tabla (etiquetar, crear ticket, marcar leído), con `DRY_RUN` activo por defecto, idempotencia por identificador de mensaje, un ticket por campaña (huella = remitente + asunto normalizado + dominios de URLs), sin eliminar correos, con permisos OAuth mínimos, y registrando la acción ejecutada o simulada. La notificación al usuario nunca afirma "seguro".

**Why this priority**: las acciones tienen efectos externos reales (mover correos, crear tickets). Sin idempotencia y simulacro, se repiten o actúan sobre correos no verificados.

**Independent Test**: con dobles de Gmail y Jira, procesar el mismo mensaje dos veces y verificar que las acciones se ejecutan una sola vez; con `DRY_RUN=true`, verificar que no se ejecuta ninguna escritura.

**Acceptance Scenarios**:

1. **AC-ACT-01**: con `DRY_RUN=true` no se ejecuta ninguna escritura en Gmail ni Jira.
2. **AC-ACT-02**: procesar dos veces el mismo identificador de mensaje ejecuta las acciones una sola vez.
3. **AC-ACT-03**: ninguna ruta de código elimina correos.
4. **AC-ACT-04**: un asunto con HTML, markup de Jira o 10 000 caracteres se escapa y trunca en el ticket.
5. **AC-ACT-05**: cada análisis registra qué acción se ejecutó o simuló.
6. **AC-ACT-06**: cada veredicto de la tabla (RF1) produce exactamente las acciones indicadas.
7. **AC-ACT-07**: dos correos de la misma campaña crean un solo ticket y el segundo se vincula al primero.
8. **AC-ACT-08**: si Jira falla, la acción de Gmail se mantiene, el error se registra y el correo no se reprocesa en bucle.

### Edge Cases

- Mismo mensaje procesado dos veces.
- Dos correos de la misma campaña (huella idéntica).
- Asunto con HTML, markup de Jira, 10 000 caracteres.
- Jira caído durante la acción.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Tabla de acciones: `malicioso` etiqueta "Phishing Alertas", sale de la bandeja y crea ticket; `sospechoso` o `revision_manual` etiqueta "Revisar Seguridad" y crea ticket de menor prioridad; `sin_indicadores` marca como leído sin mensaje de "seguro" y sin ticket.
- **FR-002** (RF2): Modo `DRY_RUN` (activo por defecto): registra lo que habría hecho y no toca Gmail ni Jira.
- **FR-003** (RF3): Idempotencia por identificador del mensaje: una segunda ejecución no repite acciones.
- **FR-004** (RF4): Un ticket por campaña (huella = remitente + asunto normalizado + dominios de URLs), con prioridad según severidad, indicadores de compromiso y enlace al análisis; textos del atacante escapados y truncados.
- **FR-005** (RF5): Solo etiquetar, marcar y archivar; nunca eliminar correos. Permisos OAuth mínimos.
- **FR-006** (RF6): Registrar la acción ejecutada o simulada en el análisis.
- **FR-007** (RF7): Notificación al usuario con redacción medida, sin afirmar "seguro".

## Success Criteria

### Measurable Outcomes

- **SC-001**: las acciones son idempotentes por identificador de mensaje.
- **SC-002**: `DRY_RUN` activo por defecto no toca Gmail ni Jira.
- **SC-003**: nunca se eliminan correos y la notificación nunca afirma "seguro".

## Assumptions

- **Fuera de alcance**: el cálculo del veredicto y la persistencia general (spec 11).
- **Hint para plan**: Adapter para Gmail y Jira, tabla acción-por-veredicto como datos, Command para cada acción con modo simulado; dobles de prueba para ambos servicios.
