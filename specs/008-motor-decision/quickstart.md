# Quickstart: Motor de Decisión Determinista

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contract**: [contracts/motor-decision.md](./contracts/motor-decision.md)

Guía de validación ejecutable de la spec 008. Sin código de implementación: solo
comandos y resultados esperados.

## 1. Previos

```powershell
# Ambiente (Windows, Python 3.11 local / 3.10+ requerido)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt     # sin dependencias nuevas en esta spec

# .env — no se requieren nuevas variables para el motor (es función pura)
# Las variables de specs 003–007 deben estar configuradas si se prueba
# integración end-to-end, pero las pruebas unitarias NO las necesitan.
```

## 2. Validación por escenarios

### V1 — Reglas duras (AC-DEC-01)

Cada regA R1–+ R5 tiene una prueba que la activa y otra que no.

```powershell
python -m pytest tests/unit/test_ac_dec_01_reglas.py -v
```

**Esper> Esperado**: 10 passed (5 reglas × 2 pruebas cada una).

### V2 — Tabla de decisión en límites (AC-DEC-02)

Score 29, 30, 75 y 76, con y sin confirmación del agente.

```powershell
python -m pytest tests/unit/test_ac_dec_02_tabla.py -v
```

**Esperado**: ≥ 8 passed (4 scores × 2 estados de agente, parametrizados).

### V3 — Verificación incompleta → revision_manual (AC-DEC-03)

Con VT caído y sin otras señales, el veredicto NUNCA es `sin_indicadores`.

```powershell
python -m pytest tests/unit/test_ac_dec_03_incompleta.py -v
```

**Esperado**: passed.

### V4 — Determinismo (AC-DEC-04)

El mismo correo analizado 10 veces da el mismo veredicto y score.

```powershell
python -m pytest tests/unit/test_ac_dec_04_determinismo.py -v
```

**Esperado**: passed (propiedad hypothesis con 10 ejemplos).

### V5 — Sin "seguro" (AC-DEC-05)

Ninguna salida del motor contiene la palabra "seguro".

```powershell
python -m pytest tests/unit/test_ac_dec_05_sin_seguro.py -v
```

**Esperado**: passed.

### V6 — Cobertura 100 % ramas (AC-DEC-06)

```powershell
python -m pytest tests/unit/ -k "dec" --cov=src/level2_agent/decision/motor --cov-branch --cov-fail-under=100
```

**Esperado**: 100 % ramas en `motor.py`.

### V7 — Agente no baja regla dura (AC-DEC-07)

Con R1 activa y el agente diciendo "no es phishing", el veredicto sigue
siendo `malicioso`.

```powershell
python -m pytest tests/unit/test_ac_dec_07_agente_no_baja.py -v
```

**Esperado**: passed.

### V8 — Trazabilidad AC→prueba

```powershell
python scripts/check_trazabilidad_ac.py --spec specs/008-motor-decision/spec.md
```

**Esperado**: `[PASS] trazabilidad_ac (7 AC cubiertos)`.

### V9 — Compuerta completa

```powershell
python scripts/verify.py
```

**Esperado**: exit 0 (todas las compuertas PASS; dependencias = advertencia
no bloqueante preexistente).

### V10 — Regresión del pipeline

```powershell
python tests/test_pipeline.py
```

**Esperado**: `benign` PASS, `malicious` PASS (`ai_agent` puede fallar
preexistente — requiere Gemini/Mongo vivos).

### V11 — Sin wiring en agent.py

```powershell
git diff main --stat -- src/level2_agent/agent.py src/gmail_integration
```

**Esperado**: vacío — el motor NO se conecta al pipeline en esta spec.

## 3. `[VERIFICAR]` items

| ID | Item | Razón |
|---|---|---|
| V1 | Interacción real del agente (spec 009) con el motor | Requiere spec 09 implementada |
| V2 | Comportamiento end-to-end con VT real | Requiere clave VT válida y Mongo |
| V3 | 100 % ramas en integración con orquestador 009 | Requiere spec 09 |
