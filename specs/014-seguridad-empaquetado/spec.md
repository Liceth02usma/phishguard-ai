# Feature Specification: Seguridad, Configuración y Empaquetado

**Feature Branch**: `chore/seguridad-empaquetado`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Dejar el sistema configurable, seguro por defecto, empaquetado y operable por alguien que no participó en el desarrollo."

## Context

**Problema**: la configuración está dispersa, las credenciales de Gmail son de escritorio, no hay contenedor ni guía de operación, y los controles de seguridad no están consolidados.

**Objetivo**: dejar el sistema configurable, seguro por defecto, empaquetado y operable por alguien que no participó en el desarrollo.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulos M11 y M15.

**Depende de**: 12.

## User Scenarios & Testing

### User Story 1 - Configuración única, seguro por defecto, empaquetado y operable (Priority: P1)

Un único módulo de configuración valida variables al iniciar y falla con mensaje claro si falta una obligatoria. Autenticación de API por clave con comparación en tiempo constante. Logs JSON sin secretos ni cuerpos de correo. Imagen de contenedor con usuario no root y composición para desarrollo (Windows y Linux). Dependencias con versión fija separadas por producción y desarrollo. CI con lint, tipos, pruebas con cobertura, `pip-audit` y detección de secretos. Credenciales fuera de la raíz. README reescrito, CHANGELOG y runbook.

**Why this priority**: consolida la seguridad y operabilidad. Sin esto, el sistema no es desplegable ni auditable.

**Independent Test**: faltar una variable obligatoria y verificar que el servicio no inicia (exit ≠ 0) nombrando la variable; ejecutar el contenedor y verificar usuario no root; alguien externo instala y ejecuta la demo en ≤ 20 minutos siguiendo solo el README.

**Acceptance Scenarios**:

1. **AC-SEC-01**: el detector de secretos no reporta hallazgos en el repositorio ni en su historial.
2. **AC-SEC-02**: una petición sin `X-API-Key` válida devuelve 401 (salvo `health`).
3. **AC-SEC-03**: los logs de una ejecución completa no contienen el cuerpo del correo, `VT_API_KEY`, la clave del modelo ni tokens.
4. **AC-SEC-04**: `pip-audit` no reporta vulnerabilidades altas o críticas.
5. **AC-SEC-05**: el contenedor se ejecuta con usuario no root.
6. **AC-SEC-06**: faltando una variable obligatoria, el servicio no inicia (código de salida distinto de 0) y el mensaje nombra la variable.
7. **AC-SEC-07**: alguien que no participó instala y ejecuta la demo en ≤ 20 minutos siguiendo solo el README.

### Edge Cases

- Variable obligatoria faltante (servicio no inicia, mensaje nombra la variable).
- Contenedor en Windows y Linux.
- Comparación de API key en tiempo constante.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Un único módulo de configuración que valida las variables al iniciar y falla con mensaje claro si falta una obligatoria (incluye las variables nuevas del plan: `API_KEYS`, `CORS_ORIGINS`, `VT_TIER`, `VT_RPM`, `VT_DAILY`, `VT_MAX_POR_CORREO`, `VT_UPLOAD_UNKNOWN`, `VT_SUBMIT_UNKNOWN_URLS`, `LLM_MAX_DIARIO`, `DRY_RUN`, `DOMINIOS_PROPIOS`, `MARCAS_PROTEGIDAS`, `ANALISIS_TIMEOUT_S`, `WORKERS`).
- **FR-002** (RF2): Autenticación de la API por clave con comparación en tiempo constante.
- **FR-003** (RF3): Logs JSON estructurados sin cuerpos de correo, claves ni tokens.
- **FR-004** (RF4): Imagen de contenedor con usuario no root y composición para desarrollo; funciona en Windows y Linux.
- **FR-005** (RF5): Dependencias con versión fija, separadas en producción y desarrollo.
- **FR-006** (RF6): Integración continua con lint, tipos, pruebas con cobertura, `pip-audit` y detección de secretos.
- **FR-007** (RF7): Eliminar de la raíz del proyecto cualquier credencial y documentar el acceso a Gmail (decisión pendiente: escritorio solo para desarrollo).
- **FR-008** (RF8): Reescribir `README.md`, crear `CHANGELOG.md` y un runbook (qué hacer si VirusTotal agota su cuota, si el modelo falla, ante una campaña masiva y cómo rotar claves).

## Success Criteria

### Measurable Outcomes

- **SC-001**: sin secretos en el repo ni su historial; sin vulnerabilidades altas/críticas.
- **SC-002**: el contenedor corre como usuario no root en Windows y Linux.
- **SC-003**: un operador externo instala y ejecuta la demo en ≤ 20 minutos siguiendo solo el README.

## Assumptions

- **Fuera de alcance**: despliegue en un proveedor concreto y gestión de secretos en la nube.
- **Hint para plan**: `pydantic-settings`, `structlog` o `logging` con formateador JSON, `Dockerfile` multietapa.
