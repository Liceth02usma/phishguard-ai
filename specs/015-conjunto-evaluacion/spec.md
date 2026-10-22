# Feature Specification: Conjunto de Evaluación Etiquetado

**Feature Branch**: `test/conjunto-evaluacion`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Un conjunto etiquetado versionado y un informe automático que mida el desempeño y bloquee la integración si baja de las metas."

## Context

**Problema**: no hay forma objetiva de saber si el detector cumple las metas (recall ≥ 95 %, falsos positivos ≤ 2 %) ni de calibrar los umbrales.

**Objetivo**: un conjunto etiquetado versionado y un informe automático que mida el desempeño y bloquee la integración si baja de las metas.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M13.

**Depende de**: 08 (puede empezar antes, desde la 02).

## User Scenarios & Testing

### User Story 1 - Conjunto etiquetado + informe de desempeño (Priority: P1)

Un conjunto de ≥ 300 correos (≥ 100 legítimos, ≥ 100 phishing público, ≥ 100 difíciles) separado del de entrenamiento, versionado, con fixtures tratadas como datos (Art. 0) y sin malware real (sintéticos o EICAR). Un script calcula recall, tasa de falsos positivos, matriz de confusión y tiempo medio, y los guarda con las versiones de pesos y modelo. 10 casos de inyección de instrucciones. Respuestas de VT y modelo grabadas para reproducibilidad sin red. Un paso de CI falla si recall < 95 % o FP > 2 %.

**Why this priority**: sin conjunto etiquetado, no se puede verificar AC-SCO-04 (recall ≥ 95 %, FP ≤ 2 %) ni detectar regresiones del detector.

**Independent Test**: ejecutar el script de evaluación dos veces sin cambios y verificar métricas idénticas; bajar el recall a 94,9 % y verificar que CI falla; a 95,0 % y verificar que pasa.

**Acceptance Scenarios**:

1. **AC-TEST-01**: el conjunto existe con el tamaño y la composición de RF1 y su verificación automática lo confirma.
2. **AC-TEST-02**: no hay identificadores comunes entre el conjunto de evaluación y el de entrenamiento.
3. **AC-TEST-03**: el informe es reproducible: dos ejecuciones sin cambios dan métricas idénticas.
4. **AC-TEST-04**: un cambio que baja el recall a 94,9 % hace fallar el paso de integración continua; 95,0 % pasa (valores límite).
5. **AC-TEST-05**: ningún caso de inyección cambia el veredicto frente a su versión sin la frase.
6. **AC-TEST-06**: ningún fixture contiene adjuntos con malware real.

### Edge Cases

- Recall 94,9 % vs 95,0 % (límite de CI).
- 10 casos de inyección (cuerpo, asunto, texto oculto, nombre de adjunto).
- Ejecución del informe dos veces (reproducibilidad).

## Requirements

### Functional Requirements

- **FR-001** (RF1): Conjunto de al menos 300 correos: ≥ 100 legítimos (anonimizados), ≥ 100 de phishing de fuentes públicas y ≥ 100 casos difíciles (BEC sin enlaces, notificaciones legítimas con urgencia).
- **FR-002** (RF2): El conjunto está separado del usado para entrenar los pesos genéticos (sin identificadores en común) y versionado con su etiquetado.
- **FR-003** (RF3): Fixtures tratadas solo como datos (Artículo 0); sin adjuntos reales de malware (se usan archivos sintéticos o el estándar EICAR).
- **FR-004** (RF4): Un script calcula recall, tasa de falsos positivos, matriz de confusión y tiempo medio, y los guarda con las versiones de pesos y de modelo.
- **FR-005** (RF5): Un conjunto de 10 casos de inyección de instrucciones (cuerpo, asunto, texto oculto, nombre de adjunto).
- **FR-006** (RF6): Respuestas de VirusTotal y del modelo grabadas para que la evaluación sea reproducible sin red.
- **FR-007** (RF7): Un paso de integración continua falla si recall < 95 % o falsos positivos > 2 %.

### Key Entities

- **ConjuntoEvaluacion**: ≥ 300 correos etiquetados, versionados, separados del entrenamiento.
- **InformeDesempeno**: recall, tasa de FP, matriz de confusión, tiempo medio, versiones de pesos y modelo.

## Success Criteria

### Measurable Outcomes

- **SC-001**: el conjunto tiene ≥ 300 correos con la composición indicada, sin solapamiento con el entrenamiento.
- **SC-002**: el informe es reproducible sin red (respuestas grabadas).
- **SC-003**: CI bloquea la integración cuando recall < 95 % o FP > 2 %.

## Assumptions

- **Fuera de alcance**: reentrenar el algoritmo genético y recolectar correos reales de clientes.
- **Hint para plan**: datos en archivos versionados, script de evaluación con dobles grabados; la anonimización se documenta y no depende de herramientas externas.
