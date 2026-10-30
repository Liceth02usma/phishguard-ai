# Implementation Plan: Persistencia y Métricas de Análisis

**Branch**: `feature/persistencia-metricas` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

## Summary

Cada análisis se persiste en MongoDB con retención TTL (90d), sin HTML original
ni adjuntos, con correo enmascarado. Métricas (total, por veredicto, % sin modelo,
duración media, por día en America/Bogota, indicadores frecuentes, tasa FP,
consultas VT y aciertos caché) se calculan sobre los datos. Datos de siembra
deterministas (100 análisis) para validación. Borrado de análisis + caché asociada.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pymongo (ya instalado), pydantic (ya instalado), pytz (ya instalado). **0 dependencias nuevas.**

**Storage**: MongoDB `phishguard.analyses` (TTL 90d), `phishguard.analyses_fallidos` (TTL 30d), índices por fecha y veredicto.

**Testing**: pytest + dobles de prueba (MongoDoble in-memory). Cero conexiones reales a MongoDB.

**Target Platform**: Windows (primary), cross-platform

**Project Type**: library (módulo del pipeline PhishGuard)

**Performance Goals**: Escritura < 100ms por análisis. Métricas < 500ms sobre 1000 documentos.

**Constraints**: No persistir HTML original ni adjuntos (FR-002, Art. V.4). Retención TTL exacta (FR-001). Siembra determinista sin aleatoriedad (FR-006).

**Scale/Scope**: ~100 análisis/día. Métricas sobre rango de hasta 90 días.

## Constitution Check

| Artículo | Requisito | Estado | Nota |
|---|---|---|---|
| Art. 0 | Integridad de instrucciones | PASS | Persistencia es código determinista, no modelo |
| Art. I.1 | Rama creada primero | PASS | `feature/persistencia-metricas` ya existe |
| Art. I.5 | Conventional Commits | PASS | `feat(per): …` |
| Art. II.1 | Pruebas primero | PASS | TDD con dobles |
| Art. II.2 | ≥3 técnicas | PASS | Partición de equivalencia (veredictos), valores límite (rangos 7/30/90), pruebas de contrato |
| Art. II.3 | Cobertura ≥80% | PLAN | Objetivo del plan |
| Art. III.1 | Archivos ≤500 líneas | PASS | 6 módulos, cada uno < 200 líneas estimadas |
| Art. III.4 | mypy --strict | PASS | Override en pyproject.toml |
| Art. III.5 | Patrones de diseño | PASS | Repository (MongoDB), Factory (siembra) |
| Art. III.6 | Sin números mágicos | PASS | Constantes en `modelos.py` |
| Art. V.1 | "seguro" jamás como veredicto | PASS | Veredicto es del motor de decisión (spec 008) |
| Art. V.4 | Datos personales enmascarados | PASS | FR-002: correo enmascarado antes de persistir |
| Art. VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..006; fuera: endpoints HTTP (spec 012) |

## Project Structure

### Documentation (this feature)

```text
specs/011-persistencia-metricas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── persistencia.md
└── tasks.md
```

### Source Code (repository root)

```text
src/level2_agent/persistencia/
├── __init__.py          # Public API
├── modelos.py           # AnalisisPersistido, Metricas, constantes TTL
├── repositorio.py       # RepositorioAnalisis (write/read/delete/metrics)
├── metricas.py          # calcular_metricas() — agregaciones puras sobre lista
├── siembra.py           # sembrar_datos() — 100 análisis deterministas
└── borrado.py           # borrar_analisis() — elimina doc + caché VT

tests/unit/
├── dobles_persistencia.py
├── test_ac_per_01_sin_html_adjuntos.py
├── test_ac_per_02_indices_ttl.py
├── test_ac_per_03_metricas_siembra.py
├── test_ac_per_04_por_dia.py
├── test_ac_per_05_tasa_fp.py
├── test_ac_per_06_siembra_idempotente.py
└── test_ac_per_07_borrado.py
```

**Structure Decision**: Single project, paquete nuevo `src/level2_agent/persistencia/` siguiendo el patrón de specs 003–010.

## Complexity Tracking

Sin violaciones a la constitución.
