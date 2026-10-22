# Quickstart: Compuertas de Calidad Automáticas

**Spec**: [spec.md](spec.md) | **Date**: 2026-10-22

Guía de validación end-to-end. Los detalles de implementación van en `tasks.md`.

## Prerrequisitos

- Python 3.10+ activado (`.venv\Scripts\activate` en Windows).
- `gitleaks` instalado y en PATH (o path configurable vía env `GITLEAKS_BIN`).
- Dependencias de desarrollo: `pip install pytest pytest-cov ruff mypy pip-audit pre-commit`.

## Validación 1 — comando único pasa en repo limpio

```powershell
python scripts/verify.py
```

**Esperado**: las 8 compuertas en `[PASS]`, exit `0`.

## Validación 2 — longitud de archivos (AC-CAL-01, valor límite)

Crear temporalmente un `.py` de 501 líneas en `tests/`, ejecutar `python scripts/verify.py` y verificar que `longitud_archivos` está en `[FAIL]` con el archivo listado y exit `1`. Quitar el archivo y verificar que vuelve a `[PASS]`. (Esto lo cubre la prueba `test_check_longitud_archivos.py` con un tmp dir; no se commitea el archivo de 501 líneas.)

## Validación 3 — nombre de rama (AC-CAL-02, tabla de decisión)

```powershell
python scripts/check_nombre_rama.py --rama feature/analisis-urls   # PASS, exit 0
python scripts/check_nombre_rama.py --rama Feature/x               # FAIL, exit 1
python scripts/check_nombre_rama.py --rama 001-analisis            # FAIL, exit 1
python scripts/check_nombre_rama.py --rama main                    # PASS (exenta), exit 0
```

## Validación 4 — trazabilidad AC→prueba (AC-CAL-05)

```powershell
python scripts/check_trazabilidad_ac.py --spec specs/000-calidad-base/spec.md
```

**Esperado**: exit `0` y sin AC listados (todos `AC-CAL-01..06` tienen prueba marcada con `@pytest.mark.ac`).

## Validación 5 — secretos (AC-CAL-04)

```powershell
gitleaks detect --source . --no-banner
```

**Esperado**: sin hallazgos en el repo. La prueba unitaria verifica la detección con una cadena tipo API key en un tmp dir.

## Validación 6 — CI (AC-CAL-06)

Abrir un PR contra `main`. El workflow `.github/workflows/verify.yml` ejecuta `python scripts/verify.py`. Si alguna compuerta falla, el check del PR queda rojo y bloquea el merge.

## Validación de la spec completa

```powershell
pytest tests/unit/ -v --cov=scripts --cov-branch --cov-fail-under=80
```

**Esperado**: todas las pruebas de los scripts de compuertas en verde, cobertura ≥80 % líneas y ramas, cada AC-CAL-01..06 con su prueba marcada.

## Referencias

- Contrato del comando `verify` y marker `ac`: [contracts/verify-cli.md](contracts/verify-cli.md)
- Modelos en memoria: [data-model.md](data-model.md)
- Decisiones de diseño: [research.md](research.md)
