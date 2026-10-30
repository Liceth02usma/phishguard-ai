# Quickstart: Agente de IA Sin Estado

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contract**: [contracts/agente-ia.md](./contracts/agente-ia.md)

Guía de validación ejecutable de la spec 009. Sin código de implementación.

## 1. Previos

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt     # sin dependencias nuevas

# .env — variables requeridas:
# GOOGLE_API_KEY (solo para integración real; pruebas usan simulador)
# MONGODB_ATLAS_CLUSTER_URI (RAG; opcional en pruebas)
# LLM_MAX_DIARIO=100 (tope diario de llamadas)
# LLM_MODELO=models/gemini-2.5-flash-lite (modelo por defecto)
```

## 2. Validación por escenarios

### V1 — Herramientas del agente (AC-AGT-01)

```powershell
python -m pytest tests/unit/test_ac_agt_01_herramientas.py -v
```

**Esperado**: passed — la lista de herramientas es exactamente `[busqueda_vectorial]`.

### V2 — Resistencia a inyección (AC-AGT-02)

```powershell
python -m pytest tests/unit/test_ac_agt_02_inyeccion.py -v
```

**Esperado**: 10 passed — veredicto no cambia con instrucciones inyectadas.

### V3 — Esquema de salida (AC-AGT-03)

```powershell
python -m pytest tests/unit/test_ac_agt_03_esquema.py -v
```

**Esperado**: passed — salida invalidada → 1 reintento → revision_manual.

### V4 — Agente no baja regla dura (AC-AGT-04)

```powershell
python -m pytest tests/unit/test_ac_agt_04_regla_dura.py -v
```

**Esperado**: passed — verificado junto con spec 08.

### V5 — Tope diario (AC-AGT-05)

```powershell
python -m pytest tests/unit/test_ac_agt_05_tope.py -v
```

**Esperado**: passed — N-1 llama modelo, N llama modelo, N+1 → revision_manual.

### V6 — Sin llamadas al modelo real (AC-AGT-06)

```powershell
python -m pytest tests/unit/test_ac_agt_06_simuladas.py -v
```

**Esperado**: passed — todas las pruebas usan respuestas simuladas.

### V7 — Compuerta completa

```powershell
python scripts/verify.py
```

**Esperado**: exit 0.

### V8 — Regresión del pipeline

```powershell
python tests/test_pipeline.py
```

**Esperado**: benign PASS, malicious PASS (ai_agent puede fallar preexistente).

## 3. `[VERIFICAR]` items

| ID | Item | Razón |
|---|---|---|
| V1 | Fuentes RAG existentes y versionadas | Requiere auditoría manual (FR-006) |
| V2 | Modelo final (Gemini vs alternativas) | Decisión del equipo (FR-008) |
| V3 | Resistencia a inyección con modelo real | Requiere GOOGLE_API_KEY y evaluación empírica |
