# Quickstart: validación del scoring (spec 007)

**Rama**: `feature/scoring-genetico` · **Requisitos**: Python 3.11, `pip install -r requirements.txt`, sin red para las pruebas unitarias.

## V1 — Suite de la spec (rojo → verde)

```powershell
# 1. RED: antes de implementar, las pruebas de la spec DEBEN fallar por ModuleNotFoundError/assert
python -m pytest tests/unit/ -k "sco or pesos or genetico" -q

# 2. VERDE: tras implementar
python -m pytest tests/unit/ -k "sco or pesos or genetico" -q
```

Esperado (verde): todos los tests `AC-SCO-01..06` + `test_pesos` + `test_genetico_genes` + `test_scoring_motor` en verde, sin red (doubles inyectados).

## V2 — Compuerta completa

```powershell
python scripts/verify.py
```

Esperado: `EXIT=0` (lint, tipos, cobertura ≥ umbral con los `--cov` nuevos de `scoring/`, `pesos.py` y `genetic_logic.py`, trazabilidad, secretos, longitud, nombre de rama).

## V3 — Trazabilidad AC → pruebas

```powershell
python scripts/check_trazabilidad_ac.py --spec specs/007-scoring-genetico/spec.md
```

Esperado: AC-SCO-01…06 todos cubiertos, exit 0.

## V4 — Checks puntuales de los AC

```powershell
python -m pytest tests/unit/test_ac_sco_01_score_bajo.py -q      # 0 genes => score_genetico < 30 (sesgo -1.0 ⇒ 26.89)
python -m pytest tests/unit/test_ac_sco_02_monotonicidad.py -q   # propiedades: bandera extra nunca baja el score
python -m pytest tests/unit/test_ac_sco_03_version.py -q         # ScoreFinal.version_pesos == "pesos_v1" (y del reporte)
python -m pytest tests/unit/test_ac_sco_05_limites.py -q         # tabla 59/60/61 → tope 60; 99/100/101 → min(100,·)
python -m pytest tests/unit/test_ac_sco_06_palabra_completa.py -q # "urgente" no coincide en "insurgente"
```

## V5 — Archivo de pesos versionado

```powershell
python -c "from src.level3_logic.pesos import cargar_pesos; p = cargar_pesos(); print(p.version, p.sesgo, len(p.pesos))"
# Esperado: pesos_v1 -1.0 32
```

Si el archivo falta o el schema es inválido: `PesosError` (fallo ruidoso, Art. III.9) — nunca un default silencioso.

## V6 — Pipeline legado (opcional, vivo: requiere `GOOGLE_API_KEY`)

```powershell
python tests/test_pipeline.py
```

Esperado: `malicious` sigue en ruta maliciosa; `benign` en ruta benigna; `ai_agent` puede cambiar de ruta (0 genes ya no da 50 — SC-001) → si cambia, se ajusta **solo** la metadata `_test` de la fixture con el motivo en el commit y **aprobación del usuario** (Art. II.7, research D10). El caso `ai_agent` ya fallaba por una causa preexistente (JSON del Gemini) no relacionada.

## V7 — AC-SCO-04 (report-only; requiere convivir con la spec 015)

El conjunto etiquetado y el harness viven en la rama paralela `test/conjunto-evaluacion` (spec 015). Cuando ambas ramas estén mergeadas en `main` (o en una rama de integración):

```powershell
python scripts/evaluar_desempeno.py --modo grabado
```

Esperado: informe con recall ≥ 95 % y falsos positivos ≤ 2 % (metas). **Si no se cumple, se informa el resultado real en el informe de la spec sin ajustar umbrales ni pesos por cuenta propia** (AC-SCO-04 / Art. VI.2). Este paso no bloquea la implementación: queda como verificación post-merge documentada en el informe final.

## V8 — Revisión de pesos negativos (FR-007)

Con `data/evaluacion/fuente_entrenamiento/100correos.csv` (32 genes + label), calcular la correlación de cada gen con la etiqueta y documentar en el informe de la spec qué pesos negativos contradicen los datos (p. ej. `apelacion_miedo = −0.871`). **Solo se documenta** (reentrenar está fuera de alcance); el resultado alimenta la futura calibración `pesos_vN`.

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `PesosError` en todos los tests | Falta `data/pesos/pesos_v1.json` (la tarea T0xx lo crea con los 32 pesos de `PESOS_AG`) |
| `test_ac_sco_05` falla en 61 puntos | Se usó el total acotado de 003 como tope final en vez de aplicar `min(60, suma)` (research D1) |
| Cobertura global baja | Faltó agregar los `--cov` de `scoring`/`pesos`/`genetic_logic` en `verify.py` (research D8) |
| Test de 003/004 afectado | No deberían: `banderas/`, `analisis_urls/` y `adjuntos/` no se modifican |
