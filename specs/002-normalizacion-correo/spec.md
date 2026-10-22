# Feature Specification: Normalización y Saneado de Correo

**Feature Branch**: `feature/normalizacion-correo`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Convertir cualquier entrada (Gmail o API) en un objeto único, acotado y saneado, listo para las verificaciones posteriores."

## Context

**Problema**: el sistema recibe correos de Gmail y de la futura API con formas distintas, sin límites de tamaño ni saneado, y sin conservar datos que los análisis posteriores necesitan (cabeceras repetidas, adjuntos, URLs).

**Objetivo**: convertir cualquier entrada en un objeto único, acotado y saneado, listo para las verificaciones posteriores.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M02.

**Depende de**: 00, 01.

## User Scenarios & Testing

### User Story 1 - Parseo y normalización de cualquier correo a EmailData (Priority: P1)

Un correo desde Gmail o desde la API (modo `.eml` o JSON) se convierte en un objeto `EmailData` único con cabeceras ordenadas, texto limpio, URLs, adjuntos con hash y origen, respetando límites duros y enmascarando datos personales antes de persistir o enviar al modelo.

**Why this priority**: todas las specs posteriores (03–08) consumen este objeto. Sin normalización acotada y saneada, no hay base confiable para el análisis.

**Independent Test**: dar un correo MIME/`.eml` y verificar el objeto `EmailData` resultante, sus límites y el enmascarado.

**Acceptance Scenarios**:

1. **AC-NORM-01**: un correo con 2 cabeceras `Received` conserva ambas y en orden.
2. **AC-NORM-02**: un HTML con script, texto oculto y comentarios produce texto limpio sin ellos.
3. **AC-NORM-03**: cada límite de FR-004 activa `LIMITE_EXCEDIDO` (una prueba por límite, incluyendo el valor justo en el límite y uno por encima).
4. **AC-NORM-04**: lo persistido y lo enviado al modelo no contiene correos electrónicos ni secuencias de 13 a 19 dígitos sin enmascarar (incluye pruebas basadas en propiedades con cadenas generadas).
5. **AC-NORM-05**: `juan.perez@empresa.com` se convierte en `j***@empresa.com`.
6. **AC-NORM-06**: un correo con cuerpo vacío, sin cabeceras o con codificación inválida no lanza excepción no controlada y se marca para revisión manual.

### Edge Cases

- Correo en el límite exacto de 25 MB y uno por encima.
- Texto para el modelo justo en 20 000 caracteres y uno por encima.
- 200 URLs (límite) y 201; 20 adjuntos y 21; 10 niveles MIME y 11.
- Remitente NO se enmascara.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Un modelo `EmailData` ampliado con: identificador del mensaje, lista ordenada de cabeceras (pares nombre y valor, conservando repetidas como `Received`), texto limpio, HTML original (solo en memoria, nunca persistido), lista de URLs, lista de adjuntos (nombre, tipo declarado, tamaño, SHA-256) y origen (`gmail` o `api`). [VERIFICAR] los campos del modelo actual.
- **FR-002** (RF2): Parseo de mensajes MIME y de archivos `.eml`.
- **FR-003** (RF3): Conversión de HTML a texto: se eliminan scripts, estilos, comentarios y texto oculto (display none, tamaño cero, color igual al fondo); se conserva el texto visible de los enlaces.
- **FR-004** (RF4): Límites duros: correo ≤ 25 MB; texto para el modelo ≤ 20 000 caracteres; ≤ 200 URLs; ≤ 20 adjuntos; ≤ 10 niveles de MIME anidado. Al excederlos se registra la bandera `LIMITE_EXCEDIDO` y el correo se marca para revisión manual.
- **FR-005** (RF5): Enmascarado de datos personales antes de persistir o enviar a terceros: correos electrónicos (se conserva el dominio y la primera letra de la parte local seguida de `***`) y secuencias de 13 a 19 dígitos (con o sin espacios o guiones) reemplazadas por `[NÚMERO_OCULTO]`. El remitente NO se enmascara.

### Key Entities

- **EmailData**: objeto normalizado y acotado que representa un correo listo para el pipeline. Campos: identificador, cabeceras ordenadas, texto limpio, HTML original (en memoria), URLs, adjuntos (nombre, tipo, tamaño, SHA-256), origen.

## Success Criteria

### Measurable Outcomes

- **SC-001**: cualquier entrada (Gmail, API, `.eml`) produce un `EmailData` con la misma forma.
- **SC-002**: ningún dato personal sin enmascarar llega a persistencia o al modelo.
- **SC-003**: todo límite excedido se marca como `LIMITE_EXCEDIDO` y revisión manual, sin excepciones no controladas.

## Assumptions

- **Fuera de alcance**: análisis de contenido, VirusTotal, extracción de macros o inspección de archivos comprimidos.
- **Hint para plan**: biblioteca estándar `email` con política moderna; Pydantic; funciones puras fáciles de probar; pruebas con `hypothesis` para el enmascarado.
