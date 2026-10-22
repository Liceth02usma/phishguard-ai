# Feature Specification: Compuertas de Calidad Automáticas

**Feature Branch**: `chore/calidad-base`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Dejar el repositorio con compuertas automáticas que fallen cuando se incumpla la constitución, ejecutables con un solo comando local y en CI."

## Context

**Problema**: la constitución exige cobertura, límite de líneas, nombres de rama y calidad, pero hoy nada lo hace cumplir. Sin compuertas automáticas, las reglas dependen de la buena voluntad.

**Objetivo**: dejar el repositorio con compuertas automáticas que fallen cuando se incumpla la constitución, ejecutables con un solo comando local y en integración continua.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` (secciones M11, M13 y M15) y la constitución.

**Depende de**: — (es la primera spec; habilita las compuertas para todas las demás).

## User Scenarios & Testing

### User Story 1 - Compuertas de calidad ejecutables con un solo comando (Priority: P1)

Un desarrollador o la CI ejecutan un único comando que verifica todas las reglas de la constitución (cobertura, lint, tipos, longitud, nombre de rama, secretos, dependencias) y falla si alguna se incumple, listando el motivo.

**Why this priority**: sin estas compuertas, ninguna spec posterior puede garantizar el Art. IV. Es la base que hace cumplir la constitución.

**Independent Test**: ejecutar el comando único contra un repo que viola cada regla y verificar que falla con el mensaje esperado; contra un repo limpio, pasa.

**Acceptance Scenarios**:

1. **AC-CAL-01**: un archivo de prueba con 501 líneas hace fallar la comprobación de longitud; con 500 líneas pasa (valores límite).
2. **AC-CAL-02**: los nombres `feature/analisis-urls`, `fix/x`, `chore/a-b-c` pasan la comprobación de nombre de rama; `Feature/x`, `feature/Analisis`, `001-analisis`, `feature/` y `feature/a_b` fallan.
3. **AC-CAL-03**: una prueba que baja la cobertura de un módulo nuevo por debajo de 80 % hace fallar el comando único.
4. **AC-CAL-04**: una cadena con forma de clave de API en el código hace fallar la detección de secretos.
5. **AC-CAL-05**: un criterio de aceptación sin prueba aparece en el informe de trazabilidad.
6. **AC-CAL-06**: la integración continua ejecuta el comando único y bloquea el merge si falla.

### Edge Cases

- Rama `main` y `develop` exentas de la comprobación de nombre de rama.
- Archivos que no son `.py` no se cuentan para el límite de 500 líneas.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Un comando único (por ejemplo `make verify` o un script equivalente) ejecuta: pruebas con cobertura de líneas y ramas con umbral 80 %, lint y formato, tipos estrictos, longitud de archivos, nombre de rama, auditoría de dependencias y detección de secretos.
- **FR-002** (RF2): Una comprobación falla si algún `.py` de `src/` o `tests/` supera 500 líneas y lista los archivos infractores con su cantidad de líneas.
- **FR-003** (RF3): Una comprobación falla si el nombre de la rama actual no cumple `^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$` (excepto en `main` y `develop`).
- **FR-004** (RF4): Una marca de pruebas `ac("AC-XXX-NN")` permite asociar pruebas a criterios de aceptación, y un informe lista los criterios definidos en una spec que no tienen prueba.
- **FR-005** (RF5): Comprobación de nombres según PEP 8 mediante el linter.
- **FR-006** (RF6): Configuración de pre-commit y de integración continua que ejecuta el comando único en cada pull request.
- **FR-007** (RF7): Un archivo `.gitignore` que excluye `.env`, `credenciales.json`, `token.json` y artefactos de cobertura; y un `.env.example` sin valores reales.

## Success Criteria

### Measurable Outcomes

- **SC-001**: un solo comando local valida todas las reglas de la constitución en menos de 2 minutos en un repo limpio.
- **SC-002**: cada violación de una regla produce un mensaje que nombra el archivo o la regla infractora.
- **SC-003**: la CI bloquea el merge cuando cualquier compuerta falla.

## Assumptions

- **Fuera de alcance**: pruebas de negocio del producto, despliegue y contenedores.
- **Hint para plan**: herramientas sugeridas `pytest`, `pytest-cov`, `ruff`, `mypy`, `pip-audit`, `gitleaks`, `pre-commit`; scripts propios en `scripts/` (cada uno ≤ 500 líneas y con pruebas).
