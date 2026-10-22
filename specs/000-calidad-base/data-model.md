# Data Model: Compuertas de Calidad Automáticas

**Spec**: [spec.md](spec.md) | **Date**: 2026-10-22

Esta spec es tooling (sin persistencia de aplicación). Las "entidades" son los modelos en memoria que usan los scripts de compuertas.

## Entidades

### Compuerta

Representa una verificación individual ejecutada por `verify.py`.

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `str` | Identificador (`longitud_archivos`, `nombre_rama`, `cobertura`, `trazabilidad_ac`, `secretos`, `dependencias`, `lint`, `tipos`) |
| `comando` | `list[str]` | argv que ejecuta la compuerta |
| `obligatoria` | `bool` | Si `true`, su fallo falla `verify.py` |

### ResultadoCompuerta

Resultado de ejecutar una `Compuerta`.

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `str` | Nombre de la compuerta |
| `ok` | `bool` | `true` si pasó |
| `detalles` | `list[str]` | Lista de infracciones/mensajes (ej. archivos >500 líneas con su conteo) |
| `duracion_s` | `float` | Tiempo de ejecución |

### ResultadoVerify

Agregado que devuelve `verify.py`.

| Campo | Tipo | Descripción |
|---|---|---|
| `resultados` | `list[ResultadoCompuerta]` | Una por compuerta ejecutada |
| `ok` | `bool` | `true` si todas las obligatorias pasaron |
| `resumen` | `str` | Texto humano para stdout |

### AsociacionAC

Trazabilidad criterio de aceptación → prueba (Art. II.6).

| Campo | Tipo | Descripción |
|---|---|---|
| `ac_id` | `str` | Ej. `AC-CAL-01` |
| `prueba` | `str` | `tests/unit/test_xxx.py::test_yyy` |

## Reglas de validación

- `LIMITE_LINEAS = 500` (constante, Art. III.1).
- `COBERTURA_MIN = 80` (constante, Art. II.3).
- `RAMA_REGEX = r"^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$"` (Art. I.2).
- `RAMAS_EXENTAS = {"main", "develop"}` (Art. I.4 / spec RF3).
- Un `ResultadoVerify` con `ok=false` hace que `verify.py` exit con código 1.

## Transiciones de estado

No aplica (sin persistencia ni máquinas de estado de dominio).
