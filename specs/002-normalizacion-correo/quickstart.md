# Quickstart: validación de la spec 002 (normalización)

Requisitos previos: dependencias instaladas (`pip install -r requirements.txt`, incluye
`hypothesis`), sin red necesaria para V1–V5.

## V1 — Suite de la spec con cobertura (Art. II.3)

```powershell
python -m pytest tests/unit/ -q --cov=scripts --cov=src/level2_agent/normalizacion --cov=src/level2_agent/models --cov-branch --cov-fail-under=80
```

Esperado: **0 fallos, 0 skips nuevos**; cobertura combinada ≥ 80 % y, dentro del paquete
`normalizacion/`, ≥ 80 % líneas y ramas por módulo (revisar el informe de coverage).

## V2 — Trazabilidad AC → prueba (Art. II.6)

```powershell
python scripts/check_trazabilidad_ac.py --spec specs/002-normalizacion-correo/spec.md
```

Esperado: `[PASS] … (6 AC cubiertos)` — AC-NORM-01..06.

## V3 — Compuertas completas (Art. IV.1)

```powershell
python scripts/verify.py
```

Esperado: exit 0. `lint` y `tipos` ahora incluyen `src/level2_agent/normalizacion/` y
`models.py` (D10); `cobertura` mide `scripts/` + paquete nuevo + modelos.
`dependencias` puede quedar como advertencia no bloqueante (vulns preexistentes, spec 014).

## V4 — Prueba manual del normalizador con un `.eml`

```powershell
python -c "from src.level2_agent.normalizacion import normalizar_desde_eml, enmascarar_para_terceros; e = normalizar_desde_eml(open('tests/fixtures/correo_prueba.eml','rb').read()); print(e.origen, len(e.cabeceras), e.banderas, e.revision_manual); print(enmascarar_para_terceros(e).textBody[:200])"
```

Esperado: `api <n> [] False` y texto sin correos ni dígitos largos. (El fixture `.eml` se
crea en la fase de pruebas si no existe.)

## V5 — Comportamiento de límites a mano

Crear en memoria un `.eml` con 201 URLs (o 21 adjuntos) y verificar:

```powershell
python -m pytest tests/unit/test_ac_norm_03_limites.py -q
```

Esperado: todas verdes; cada límite probado en `en el límite` (sin bandera) y `+1`
(bandera + `revision_manual`).

## V6 — Integración del poller [VERIFICAR]

`process_message` ahora llama `normalizar_desde_gmail(raw_bytes, msg_id)`. La prueba
automatizada usa un servicio Gmail falso (`test_integracion_poller.py`). La corrida contra
Gmail real requiere `credenciales.json`/`token.json` y bandeja con correo de prueba:
**queda [VERIFICAR] hasta ejecución manual** (no se ejecuta en CI ni localmente por la
ausencia controlada de credenciales).

## V7 — Lint, tipos y longitud (Art. III)

```powershell
python -m ruff check scripts/ tests/unit/ src/level2_agent/models.py src/level2_agent/normalizacion/
python -m mypy scripts/ tests/unit/
```

Esperado: ambos sin errores. `ruff` sí recibe las rutas `src/` nuevas explícitamente (sin
`force-exclude` las revisa aunque `src` esté en `extend-exclude`); `mypy` NO las pasa como
ruta — sigue los imports de `tests/unit/` hacia `src.level2_agent.*` y los evalúa con los
overrides de `pyproject.toml` (legado exento, `models.py` + `normalizacion/` estrictos),
evitando el choque "found twice" por la falta de `src/__init__.py`. Ningún `.py` > 500
líneas (lo verifica `verify.py`).

## Notas

- Los límites exactos están en `src/level2_agent/normalizacion/limites.py`
  (`LIMITE_*`); los valores salen de FR-004, no se editan en pruebas.
- La vista enmascarada es la ÚNICA vía válida hacia el LLM y la persistencia
  (`contracts/normalizacion-api.md`).
