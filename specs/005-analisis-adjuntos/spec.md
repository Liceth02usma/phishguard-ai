# Feature Specification: Análisis Estático de Adjuntos

**Feature Branch**: `feature/analisis-adjuntos`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Analizar cada adjunto de forma estática, en memoria y sin ejecutarlo, y producir banderas y hashes."

## Context

**Problema**: los adjuntos no se verifican: no se calcula su hash, no se compara su tipo real con la extensión y no se detectan macros ni archivos comprimidos peligrosos.

**Objetivo**: analizar cada adjunto de forma estática, en memoria y sin ejecutarlo, y producir banderas y hashes.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M05 y catálogo 5.3.

**Depende de**: 02.

## User Scenarios & Testing

### User Story 1 - Análisis estático seguro de adjuntos (Priority: P1)

Cada adjunto se procesa en memoria (sin escribir a disco con su nombre original, sin ejecutar, sin abrir con aplicaciones del sistema): se calculan hashes (SHA-256, MD5, SHA-1), se detecta el tipo real por magic bytes y se compara con la extensión/Content-Type, se detectan extensiones de riesgo, doble extensión, macros/enlaces externos en Office, JavaScript/OpenAction/Launch en PDF, y zips con límites y cifrado.

**Why this priority**: los adjuntos son vector de malware. El análisis estático en memoria es requisito para la consulta a VirusTotal (spec 06) y para las reglas duras del motor de decisión (spec 08).

**Independent Test**: dar un adjunto sintético y verificar hashes, banderas y que nunca se escribió a disco ni se ejecutó.

**Acceptance Scenarios**:

1. **AC-ADJ-01**: el SHA-256 calculado coincide con una referencia externa para 3 archivos de prueba.
2. **AC-ADJ-02**: el archivo estándar de prueba antivirus EICAR (cadena inofensiva) se identifica por su hash y queda disponible para la prueba integrada de la spec 06.
3. **AC-ADJ-03**: `factura.pdf.exe` activa `ADJ_DOBLE_EXTENSION`; un ejecutable renombrado a `.pdf` activa `ADJ_TIPO_NO_COINCIDE`.
4. **AC-ADJ-04**: un zip de prueba con relación mayor a 100:1 se aborta sin agotar memoria y activa `ADJ_ARCHIVO_SOSPECHOSO` (probar 99:1, 100:1 y 101:1).
5. **AC-ADJ-05**: ningún camino de código escribe adjuntos en disco con su nombre original ni los ejecuta.
6. **AC-ADJ-06**: un adjunto vacío, truncado o con nombre con `..` o rutas no lanza excepción no controlada.

### Edge Cases

- Adjunto vacío, truncado.
- Nombre con `..` o rutas absolutas.
- Relación de compresión 99:1, 100:1, 101:1.
- Zip cifrado con contraseña.
- Zip con >100 entradas o >100 MB descomprimidos.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Calcular SHA-256 (principal) y MD5 y SHA-1 (informativos) del contenido.
- **FR-002** (RF2): Detectar el tipo real por firma (magic bytes) y compararlo con la extensión y el `Content-Type` (`ADJ_TIPO_NO_COINCIDE`).
- **FR-003** (RF3): Lista configurable de extensiones de riesgo (ejecutables, scripts, accesos directos, imágenes de disco, HTML o SVG) (`ADJ_EXTENSION_RIESGO`, `ADJ_HTML`) y doble extensión (`ADJ_DOBLE_EXTENSION`).
- **FR-004** (RF4): Documentos Office: detectar macros y vínculos externos (`ADJ_MACRO`, `ADJ_ENLACE_EXTERNO`). PDF: detectar `/JavaScript`, `/OpenAction` y `/Launch` (`ADJ_PDF_ACTIVO`).
- **FR-005** (RF5): Archivos zip: listar contenido sin extraer a disco; máximo 100 entradas, 100 MB descomprimidos y relación de compresión 100:1; cifrado con contraseña (`ADJ_CIFRADO`); sospechoso (`ADJ_ARCHIVO_SOSPECHOSO`).
- **FR-006** (RF6): Procesar solo en memoria; nunca escribir el adjunto en disco con su nombre original ni ejecutarlo ni abrirlo con aplicaciones del sistema.
- **FR-007** (RF7): La política de subida a VirusTotal queda desactivada por defecto (la consulta de reputación es la spec 06).

## Success Criteria

### Measurable Outcomes

- **SC-001**: cada adjunto produce hashes correctos y banderas sin ejecutarse ni escribirse a disco.
- **SC-002**: los zips con relación >100:1 se abortan sin agotar memoria.
- **SC-003**: los archivos maliciosos de prueba se generan en memoria, no se guardan en el repositorio.

## Assumptions

- **Fuera de alcance**: consulta a VirusTotal, lectura de códigos QR y análisis dinámico (ejecución en caja de arena).
- **Hint para plan**: Strategy para detectores, `oletools`, lector de PDF de solo lectura, `zipfile` con límites; los archivos de prueba maliciosos se generan en memoria, no se guardan en el repositorio.
