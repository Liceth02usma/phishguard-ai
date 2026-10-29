# Quickstart: validación del scoring con clasificador lineal (spec 007)

**Rama**: `feature/scoring-genetico` · **Requisitos**: Python 3.11, `pip install -r requirements.txt`, sin red para pruebas unitarias.

## V1 — Suite de la spec (rojo → verde)

```powershell
python -m pytest tests/unit/ -k "sco or modelo or genetico" -q
```

## V2 — Compuerta completa

```powershell
python scripts/verify.py
```

Esperado: EXIT=0.

## V3 — Trazabilidad AC → pruebas

```powershell
python scripts/check_trazabilidad_ac.py --spec specs/007-scoring-genetico/spec.md
```

## V4 — Checks puntuales de los AC

```powershell
python -m pytest tests/unit/test_ac_sco_01_score_bajo.py -q      # 0 genes => score_clasificador < 30
python -m pytest tests/unit/test_ac_sco_02_monotonicidad.py -q   # bandera extra nunca baja
python -m pytest tests/unit/test_ac_sco_03_version.py -q         # version_modelo == "clasificador_v1"
python -m pytest tests/unit/test_ac_sco_05_limites.py -q         # tabla 59/60/61 y 99/100/101
python -m pytest tests/unit/test_ac_sco_06_palabra_completa.py -q # "urgente" ⊄ "insurgente"
```

## V5 — Modelo versionado

```powershell
python -c "from src.level3_logic.modelo import cargar_modelo; m = cargar_modelo(); print(m.version, m.intercepto, len(m.coeficientes))"
# Esperado: clasificador_v1 <intercepto> 32
```

Si el archivo falta: `ModeloError` (fallo ruidoso, Art. III.9).

## V6 — Entrenamiento del modelo (prerrequisito)

Antes de implementar el runtime, ejecutar el script de entrenamiento offline:

```powershell
pip install scikit-learn  # solo para entrenamiento
python scripts/entrenar_clasificador.py
```

Esperado: `data/modelo/clasificador_v1.json` creado; el script verifica AC-SCO-01 (0 genes → score < 30) y falla si no se cumple.

## V7 — Pipeline legado (opcional, vivo)

```powershell
python tests/test_pipeline.py
```

Si la fixture `ai_agent` cambia de ruta (0 genes ya no da 50), actualizar metadata `_test` **solo con aprobación del usuario** (Art. II.7).

## V8 — AC-SCO-04 + FR-007 (post-merge con spec 015)

```powershell
python scripts/evaluar_desempeno.py --modo grabado
```

Report-only: si recall < 95% o FP > 2%, informar sin ajustar.
