# Tasks: Persistencia y Métricas de Análisis

**Spec**: 011 · **Branch**: `feature/persistencia-metricas` · **Date**: 2026-10-30

## Phase 1: Setup

- [ ] T001: Crear paquete `src/level2_agent/persistencia/` con 6 módulos vacíos + `__init__.py`
- [ ] T002: Añadir override mypy strict para `src.level2_agent.persistencia` en `pyproject.toml`
- [ ] T003: Añadir `--cov=src/level2_agent/persistencia` y path en `scripts/verify.py`

## Phase 2: Fundacional

- [ ] T004: Implementar `modelos.py` — `AnalisisPersistido`, `Metricas`, `PorDia`, constantes TTL, `Veredicto`/`NivelSeveridad`/`Ruta`/`Origen`/`Modo`/`Retroalimentacion` literals
- [ ] T005: Implementar `__init__.py` — public API exports
- [ ] T006: Implementar `repositorio.py` — `RepositorioAnalisis` Protocol + `RepositorioReal` (pymongo) + `RepositorioDoble` (in-memory)
- [ ] T007: Implementar `repositorio.py` — `RepositorioCacheVT` Protocol + `CacheVTDoble`
- [ ] T008: Implementar `metricas.py` — `calcular_metricas()` función pura
- [ ] T009: Implementar `siembra.py` — `sembrar_datos()` 100 análisis deterministas
- [ ] T010: Implementar `borrado.py` — `borrar_analisis()` con caché VT
- [ ] T011: Implementar `dobles_persistencia.py` — `RepositorioDoble`, `CacheVTDoble`, `entrada_persistido_ejemplo()`

## Phase 3: US1 — Pruebas TDD (AC-PER-01..07)

- [ ] T012: Test AC-PER-01 — análisis guardado no contiene HTML, adjuntos ni correos sin enmascarar
- [ ] T013: Test AC-PER-02 — índices TTL existen con retenciones indicadas
- [ ] T014: Test AC-PER-03 — métricas sobre siembra: total 100, 55/15/30, 60% sin modelo
- [ ] T015: Test AC-PER-04 — por_dia tiene elemento por cada día (7, 30, 90) + zona horaria
- [ ] T016: Test AC-PER-05 — tasa FP nula sin retroalimentación, correcta cuando la hay
- [ ] T017: Test AC-PER-06 — siembra idempotente: 2 ejecuciones = 100 docs
- [ ] T018: Test AC-PER-07 — borrar elimina documento + caché VT

## Phase 4: Implementación

- [ ] T019: Implementar `guardar_analisis()` — enmascarar + persistir + verificar I1/I2
- [ ] T020: Implementar `calcular_metricas()` — total, por_veredicto, pct_sin_modelo, duracion_media
- [ ] T021: Implementar `calcular_metricas()` — por_dia con relleno de ceros + zona horaria
- [ ] T022: Implementar `calcular_metricas()` — indicadores_frecuentes, tasa_falsos_positivos, consultas_vt, aciertos_cache
- [ ] T023: Implementar `sembrar_datos()` — fórmula determinista + idempotencia
- [ ] T024: Implementar `borrar_analisis()` — eliminar doc + caché VT
- [ ] T025: Implementar `RepositorioReal` — crear índices TTL al iniciar

## Phase 5: Integración

- [ ] T026: Wiring en `gmail_poller.py` — llamar `guardar_analisis` tras cada análisis
- [ ] T027: Wiring en `agent.py` — construir `AnalisisPersistido` desde resultado del pipeline

## Phase 6: Pulido

- [ ] T028: ruff + mypy strict sobre `persistencia/`
- [ ] T029: Verificar longitud archivos ≤500 líneas
- [ ] T030: Actualizar README.md con sección M14
- [ ] T031: Actualizar AGENTS.md con arquitectura de persistencia
- [ ] T032: Marcar tareas completadas en tasks.md
