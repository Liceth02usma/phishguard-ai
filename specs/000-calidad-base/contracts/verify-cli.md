# Contract: Comando `verify` + marker `ac`

**Spec**: [spec.md](../spec.md) | **Date**: 2026-10-22

## Comando único de calidad

### Invocación

```
python scripts/verify.py
```

(Sin argumentos obligatorios. Flags opcionales `--no-cobertura`, `--solo <compuerta>` para desarrollo.)

### Salida (stdout)

Texto humano, una línea por compuerta con `[PASS]`/`[FAIL]` y un resumen final:

```
[PASS] longitud_archivos
[PASS] nombre_rama
[FAIL] cobertura — ramas 78 % < 80 % en src/level2_agent/agent.py
[PASS] trazabilidad_ac
[PASS] secretos
[PASS] dependencias
[PASS] lint
[PASS] tipos
----
Fallo: cobertura
```

### Código de salida

| Código | Significado |
|---|---|
| `0` | Todas las compuertas obligatorias pasaron |
| `1` | Al menos una compuerta obligatoria falló (lista en stdout) |
| `2` | Error de uso (argumentos inválidos) |

### Compuertas ejecutadas (en orden)

1. `longitud_archivos` — ningún `.py` de `src/` o `tests/` supera 500 líneas (RF2).
2. `nombre_rama` — rama actual cumple el regex, excepto `main`/`develop` (RF3).
3. `cobertura` — `pytest --cov --cov-branch --cov-fail-under=80` (RF1, Art. II.3).
4. `trazabilidad_ac` — todo AC definido en la spec de la rama tiene prueba marcada (RF4).
5. `secretos` — `gitleaks` sin hallazgos (RF1, AC-CAL-04).
6. `dependencias` — `pip-audit` sin vulnerabilidades altas/críticas (RF1, Art. III.8).
7. `lint` — `ruff check` sin errores (RF5, Art. III.8).
8. `tipos` — `mypy --strict` sin errores (Art. III.4).

## Marker de trazabilidad `ac`

### Registro

En `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "ac(id: str): asocia una prueba a un criterio de aceptación AC-XXX-NN (Art. II.6)",
]
```

### Uso en pruebas

```python
import pytest

@pytest.mark.ac("AC-CAL-01")
def test_archivo_501_lineas_falla():
    ...
```

### Informe de AC sin prueba

```
python scripts/check_trazabilidad_ac.py --spec specs/000-calidad-base/spec.md
```

Salida (stdout): lista de `AC-CAL-NN` definidos en la spec sin ninguna prueba marcada. Exit `0` si todos tienen prueba, `1` si falta alguno.

## `.env.example`

Archivo sin valores reales que documenta las variables de entorno del producto (constitución Art. V.3, spec RF7). Forma:

```
# Obligatorio
GOOGLE_API_KEY=
MONGODB_ATLAS_CLUSTER_URI=
# Opcional
VT_API_KEY=
JIRA_INSTANCE_URL=
JIRA_USER_EMAIL=
JIRA_API_TOKEN=
DRY_RUN=true
```

## `.gitignore` (entradas añadidas)

```
.env
credenciales.json
token.json
.coverage
.coverage.*
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```
