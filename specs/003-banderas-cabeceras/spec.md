# Feature Specification: Banderas Deterministas de Cabeceras y Remitente

**Feature Branch**: `feature/banderas-cabeceras`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Producir, para cada correo, un conjunto de banderas de cabeceras y remitente con código, severidad, puntos y detalle, sin usar IA."

## Context

**Problema**: la revisión de SPF, DKIM y DMARC depende hoy del criterio del modelo de lenguaje. Faltan señales deterministas y explicables sobre la identidad del remitente.

**Objetivo**: producir, para cada correo, un conjunto de banderas de cabeceras y remitente con código, severidad, puntos y detalle, sin usar IA.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M03 y catálogo 5.1.

**Depende de**: 02.

## User Scenarios & Testing

### User Story 1 - Banderas de cabeceras y remitente deterministas (Priority: P1)

Para cada correo normalizado, el sistema produce banderas (SPF/DKIM/DMARC, suplantación, dominio parecido, edad de dominio, etc.) con código, severidad, puntos y detalle, comparando dominios por dominio organizacional y consultando RDAP con caché y tiempo máximo, sin usar IA.

**Why this priority**: estas banderas alimentan el scoring (spec 07) y el motor de decisión (spec 08). Sin señales deterministas de identidad, el veredicto depende del modelo.

**Independent Test**: dar un correo con cabeceras conocidas y verificar el conjunto exacto de banderas activadas con sus puntos.

**Acceptance Scenarios**:

1. **AC-HDR-01**: cada bandera tiene al menos un correo que la activa y uno que no (par positivo y negativo).
2. **AC-HDR-02**: un `Authentication-Results` inyectado por un servidor externo no altera SPF, DKIM ni DMARC.
3. **AC-HDR-03**: sin `Authentication-Results` confiable, SPF, DKIM y DMARC son `desconocido` y se activa `AUTH_NO_EVALUABLE`.
4. **AC-HDR-04**: `paypa1.com` frente a la marca protegida `paypal.com` activa `DOMINIO_PARECIDO`; `empresa.com.co` frente a `empresa.com` no se confunde por subcadena.
5. **AC-HDR-05**: la suma de puntos de banderas de un correo nunca supera 60 (valor límite con banderas que sumarían 61 y 60).
6. **AC-HDR-06**: una caída o respuesta inválida de RDAP no lanza excepción y no suma puntos.

### Edge Cases

- `Authentication-Results` ausente.
- `authserv-id` de servidor externo (se ignora).
- Dominio con punycode/homoglifo.
- RDAP caído o lento (>5 s).

## Requirements

### Functional Requirements

- **FR-001** (RF1): Leer `Authentication-Results` (RFC 8601) solo cuando proviene del servidor propio (el `authserv-id` configurado). Las de servidores externos se ignoran.
- **FR-002** (RF2): Sin `Authentication-Results` confiable, SPF, DKIM y DMARC valen `desconocido` y se activa `AUTH_NO_EVALUABLE`.
- **FR-003** (RF3): Comparar dominios por dominio organizacional (lista de sufijos públicos), nunca por subcadena.
- **FR-004** (RF4): Detectar dominios parecidos a los propios o a marcas protegidas (configurables): distancia de edición ≤ 2, homoglifos y `punycode`.
- **FR-005** (RF5): Banderas del catálogo 5.1 del plan: `SPF_FALLA`, `DKIM_FALLA`, `DMARC_FALLA`, `AUTH_NO_EVALUABLE`, `REPLY_TO_DISTINTO`, `RETURN_PATH_DISTINTO`, `NOMBRE_SUPLANTA`, `DOMINIO_PARECIDO`, `DOMINIO_PUNYCODE`, `MESSAGE_ID_DISTINTO`, `RECEIVED_INCONSISTENTE`, `FECHA_ANOMALA`, `REPLY_TO_GRATUITO`, `REMITENTE_EXTERNO_COMO_INTERNO`, `DOMINIO_NUEVO`, `DOMINIO_EDAD_DESCONOCIDA` (con los puntos y severidades del catálogo; el tope de puntos de todas las banderas del correo es 60).
- **FR-006** (RF6): Consulta RDAP de la edad del dominio con caché de 7 días y tiempo máximo de 5 s; si falla, solo se registra `DOMINIO_EDAD_DESCONOCIDA` sin penalizar.

## Success Criteria

### Measurable Outcomes

- **SC-001**: cada bandera es activable por al menos un correo y desactivable por otro.
- **SC-002**: la suma de puntos de banderas nunca supera 60.
- **SC-003**: las fallas de RDAP nunca penalizan ni lanzan excepciones.

## Assumptions

- **Fuera de alcance**: URLs, adjuntos, VirusTotal y el cálculo del veredicto.
- **Hint para plan**: Strategy (una clase por bandera con interfaz común), registro de banderas, `tldextract` para dominio organizacional, Adapter para RDAP; tabla de decisión para los pares positivo/negativo.
