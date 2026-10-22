# Feature Specification: Motor de Decisión Determinista

**Feature Branch**: `feature/motor-decision`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Un único punto de decisión, determinista y explicable, que nunca declare 'sin indicadores' si una verificación obligatoria quedó incompleta."

## Context

**Problema**: el veredicto depende en parte del criterio del modelo y el sistema marca correos como seguros sin verificar. El umbral 75 es ambiguo.

**Objetivo**: un único punto de decisión, determinista y explicable, que nunca declare "sin indicadores" si una verificación obligatoria quedó incompleta.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M09.

**Depende de**: 06, 07.

## User Scenarios & Testing

### User Story 1 - Veredicto por reglas duras + tabla de decisión (Priority: P1)

Un único motor aplica primero reglas duras (R1–R5) que fijan `malicioso`, luego una tabla ordenada que combina `score_final`, la confirmación del agente y las verificaciones incompletas para producir `veredicto` (`malicioso`/`sospechoso`/`revision_manual`/`sin_indicadores`), `nivel_severidad`, `ruta`, `reglas_aplicadas`, `banderas` y `verificaciones_incompletas`. La opinión del agente puede subir el riesgo, nunca bajar una regla dura. La palabra "seguro" no aparece en ninguna salida.

**Why this priority**: el motor de decisión es el componente crítico de seguridad. Un veredicto equivocado es un falso negativo (phishing entregado) o falso positivo (correo legítimo bloqueado).

**Independent Test**: dar un caso con reglas/banderas/score/agente conocidos y verificar el veredicto, severidad y ruta; repetir 10 veces y verificar determinismo.

**Acceptance Scenarios**:

1. **AC-DEC-01**: cada regla dura R1 a R5 tiene una prueba que la activa y otra que no.
2. **AC-DEC-02**: la tabla se prueba en los límites: score 29, 30, 75 y 76, con y sin confirmación del agente.
3. **AC-DEC-03**: con VirusTotal caído y un correo sin otras señales, el veredicto es `revision_manual`, nunca `sin_indicadores`.
4. **AC-DEC-04**: el mismo correo analizado 10 veces da el mismo veredicto y score en la parte determinista.
5. **AC-DEC-05**: ninguna salida contiene la palabra "seguro".
6. **AC-DEC-06**: cobertura de ramas del motor = 100 %.
7. **AC-DEC-07**: con R1 activa y el agente diciendo "no es phishing", el veredicto sigue siendo `malicioso`.

### Edge Cases

- Score 29, 30, 75, 76 (límites de la tabla).
- Con y sin confirmación del agente en la zona gris.
- Verificación obligatoria incompleta (VirusTotal caído).
- Regla dura activa + agente en contra.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Reglas duras (la primera que aplica fija `malicioso`): R1 hash de adjunto `maliciosa`; R2 URL `maliciosa`; R3 dominio del remitente `maliciosa`; R4 SPF, DKIM y DMARC fallan y (dominio parecido o nombre que suplanta); R5 adjunto con macro o ejecutable en archivo cifrado con contraseña, de un remitente no autenticado.
- **FR-002** (RF2): Tabla en este orden: (1) verificación obligatoria incompleta, `revision_manual`; (2) `score_final >= 76`, `malicioso`; (3) `score_final` de 30 a 75 y el agente confirma phishing, `malicioso`; (4) de 30 a 75 y el agente no confirma, `sospechoso`; (5) `score_final < 30` con alguna bandera de severidad media o alta, `sospechoso`; (6) `score_final < 30` sin banderas medias o altas y con verificaciones completas, `sin_indicadores`.
- **FR-003** (RF3): Verificación obligatoria: la consulta a VirusTotal de cada hash de adjunto y de cada URL con al menos una bandera de severidad media o alta.
- **FR-004** (RF4): La opinión del agente puede subir el riesgo, nunca bajar un resultado de regla dura.
- **FR-005** (RF5): Salida: `veredicto`, `score_final`, `nivel_severidad` (Crítico para R1, R2 o R5; Alto para otro `malicioso`; Medio para `sospechoso` o `revision_manual`; Bajo para `sin_indicadores`), `ruta` (`reglas`, `heuristica`, `ia`), `reglas_aplicadas`, `banderas`, `verificaciones_incompletas`.
- **FR-006** (RF6): La palabra "seguro" no aparece en ninguna salida.

## Success Criteria

### Measurable Outcomes

- **SC-001**: una verificación obligatoria incompleta nunca produce `sin_indicadores`.
- **SC-002**: el motor es determinista: el mismo caso da el mismo veredicto.
- **SC-003**: una regla dura no puede ser revertida por el agente.

## Assumptions

- **Fuera de alcance**: ejecutar acciones (spec 10) y llamar al modelo (spec 09).
- **Hint para plan**: Chain of Responsibility o lista ordenada de reglas, tabla de decisión como estructura de datos, función pura; pruebas por tabla de decisión.
