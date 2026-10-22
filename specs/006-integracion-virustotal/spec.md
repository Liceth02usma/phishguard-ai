# Feature Specification: Integración con VirusTotal API v3

**Feature Branch**: `feature/integracion-virustotal`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Un cliente de VirusTotal API v3 determinista, con límites de tasa, caché, reintentos y cortacircuitos, que clasifique hashes, URLs, dominios e IPs."

## Context

**Problema**: VirusTotal solo se consulta para IPs y a criterio del agente. Hashes, URLs y dominios no se verifican, y no hay control de cuota, caché ni tolerancia a fallos.

**Objetivo**: un cliente de VirusTotal API v3 determinista, con límites de tasa, caché, reintentos y cortacircuitos, que clasifique hashes, URLs, dominios e IPs.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M06 (todas sus subsecciones).

**Depende de**: 04, 05.

## User Scenarios & Testing

### User Story 1 - Cliente VirusTotal con cuota, caché, reintentos y cortacircuitos (Priority: P1)

Un cliente consulta hashes (SHA-256), URLs (Base64 url-safe sin relleno), dominios e IPs, clasifica `last_analysis_stats` según umbrales configurables, controla cuota (public/premium), reintentos en 429/5xx, cortacircuitos tras 5 fallos, caché en MongoDB con TTL por tipo, y un presupuesto máximo por correo con prioridad. Un 404 es `desconocida`, nunca `limpia`. Subida de archivos y envío de URLs desactivados por defecto.

**Why this priority**: la reputación de hashes/URLs/dominios es insumo de las reglas duras (spec 08) y de la resiliencia (spec 13). Sin cuota/cortacircuitos, una campaña masiva agota la API o cuelga el análisis.

**Independent Test**: con un cliente simulado y respuestas grabadas, verificar clasificación, reintentos, cortacircuitos, caché y presupuesto sin llamada real.

**Acceptance Scenarios**:

1. **AC-VT-01**: con cliente simulado, un hash con `malicious=5` se clasifica `maliciosa`; con 404 se clasifica `desconocida`.
2. **AC-VT-02**: el identificador de URL es Base64 url-safe sin relleno (3 URLs conocidas).
3. **AC-VT-03**: con `public`, 5 consultas seguidas no exceden 4 por minuto (la quinta espera u se omite), y el tope diario de 500 se respeta tras un reinicio.
4. **AC-VT-04**: una respuesta 429 se reintenta con espera creciente y respeta `Retry-After`.
5. **AC-VT-05**: tras 5 fallos seguidos el cortacircuitos se abre y el análisis continúa con `VT_NO_DISPONIBLE`.
6. **AC-VT-06**: una segunda consulta idéntica dentro del TTL se resuelve desde la caché sin llamada externa.
7. **AC-VT-07**: los parámetros sensibles se eliminan de la URL antes de consultar y la clave no aparece en logs.
8. **AC-VT-08**: valores límite de clasificación: `malicious` 2 y 3; `suspicious` 2 y 3; `harmless + undetected` 19 y 20.
9. **AC-VT-09**: con `VT_UPLOAD_UNKNOWN=false` no se realiza ninguna petición de subida.
10. **AC-VT-10**: prueba integrada con el hash de EICAR (respuesta grabada) clasifica `maliciosa`.

### Edge Cases

- 404 → `desconocida` (no `limpia`).
- `malicious` 2 vs 3; `suspicious` 2 vs 3; `harmless+undetected` 19 vs 20.
- 429 con y sin `Retry-After`.
- 5 fallos consecutivos (cortacircuito abre).
- Presupuesto exactamente en 10 y en 11.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Consultas: archivo por SHA-256, URL (identificador en Base64 url-safe sin relleno), dominio e IP. Un 404 significa "desconocido", nunca "limpio".
- **FR-002** (RF2): Modo configurable `VT_TIER` = `public` (4 solicitudes por minuto y 500 por día, contador persistente) o `premium` (límite configurable). El modo `public` es solo para demostración: su uso en productos o servicios comerciales no está permitido por los términos de VirusTotal.
- **FR-003** (RF3): Reintentos: en 429 y 5xx hasta 3 con espera exponencial más aleatoriedad, respetando `Retry-After`; sin reintento en otros 4xx.
- **FR-004** (RF4): Cortacircuitos: tras 5 fallos consecutivos se abre 60 s; durante ese tiempo no se llama y se activa `VT_NO_DISPONIBLE`.
- **FR-005** (RF5): Caché en MongoDB con TTL: archivos 7 días; URLs, dominios e IPs 24 horas; "desconocido" 1 hora.
- **FR-006** (RF6): Presupuesto máximo de 10 consultas externas por correo (`VT_MAX_POR_CORREO`) con prioridad: hashes, URLs con banderas de riesgo, dominios, IPs, demás URLs; lo que excede activa `VT_PRESUPUESTO_AGOTADO`.
- **FR-007** (RF7): Clasificación a partir de `last_analysis_stats`: `maliciosa` si `malicious >= 3`; `sospechosa` si `malicious` es 1 o 2, o `suspicious >= 3`; `limpia` si `malicious = 0`, `suspicious <= 2` y `harmless + undetected >= 20`; `desconocida` en cualquier otro caso. "Limpia" nunca reduce el puntaje. Los umbrales son configurables.
- **FR-008** (RF8): Subida de archivos (`POST /files`) y envío de URLs desconocidas desactivados por defecto (`VT_UPLOAD_UNKNOWN=false`, `VT_SUBMIT_UNKNOWN_URLS=false`). Lo consultado a VirusTotal puede quedar visible para su comunidad: no se envían datos personales.
- **FR-009** (RF9): `VT_API_KEY` solo por entorno; nunca en logs.

## Success Criteria

### Measurable Outcomes

- **SC-001**: la clasificación respeta los umbrales configurables en sus valores límite.
- **SC-002**: el cortacircuitos abre tras 5 fallos y el análisis continúa con `VT_NO_DISPONIBLE`.
- **SC-003**: el presupuesto por correo limita a 10 consultas externas con la prioridad definida.

## Assumptions

- **Fuera de alcance**: decidir el veredicto (spec 08), subir archivos y la licencia comercial (decisión del equipo).
- **Hint para plan**: Adapter + Repository (caché), Circuit Breaker, limitador de cubeta de fichas, `httpx` asíncrono con transporte simulado; respuestas reales grabadas y anonimizadas como fixtures de contrato.
