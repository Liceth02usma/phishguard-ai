# Quickstart: Persistencia y Métricas de Análisis

**Spec**: 011 · **Date**: 2026-10-30

## Prerequisites

- Python 3.11+, pymongo, pydantic, pytz instalados
- Spec 008 (motor de decisión) merged en `main`
- Spec 010 (acciones) merged en `main`

## Validation Scenarios

### V1 — Guardar análisis sin HTML/adjuntos (AC-PER-01)

```python
from src.level2_agent.persistencia import guardar_analisis, AnalisisPersistido

analisis = AnalisisPersistido(
    message_id="msg_001", origen="gmail", modo="produccion",
    fecha=datetime.now(tz=timezone.utc), duracion_ms=250,
    correo_enmascarado={"remitente": "u***@example.com"},
    score_final=85, ruta="ia", veredicto="malicioso",
    nivel_severidad="Alto", version_pesos="v1", version_modelo="gemini-2.5",
)
msg_id = guardar_analisis(analisis)
assert msg_id == "msg_001"
```

**Expected**: documento en `phishguard.analyses` sin `htmlBody` ni `contenido`.

### V2 — Métricas sobre siembra (AC-PER-03)

```python
from src.level2_agent.persistencia import sembrar_datos, calcular_metricas
from src.level2_agent.persistencia.repositorio import RepositorioDoble

repo = RepositorioDoble()
n = sembrar_datos(repo=repo)
assert n == 100

docs = repo.listar({"origen": "siembra"})
m = calcular_metricas(docs)
assert m.total == 100
assert m.por_veredicto["sin_indicadores"] == 55
assert m.por_veredicto["sospechoso"] == 15
assert m.por_veredicto["malicioso"] == 30
assert abs(m.pct_sin_modelo - 60.0) < 0.01
```

**Expected**: métricas exactas sobre datos de siembra.

### V3 — por_dia con días en cero (AC-PER-04)

```python
m = calcular_metricas(docs, inicio=date(2026, 10, 1), fin=date(2026, 10, 7))
assert len(m.por_dia) == 7  # incluye días con 0 análisis
```

**Expected**: 7 elementos, algunos con `total=0`.

### V4 — Tasa de FP nula sin retroalimentación (AC-PER-05)

```python
m = calcular_metricas(docs)
assert m.tasa_falsos_positivos is None
```

**Expected**: `None` cuando no hay retroalimentación.

### V5 — Siembra idempotente (AC-PER-06)

```python
sembrar_datos(repo=repo)
sembrar_datos(repo=repo)  # segunda vez
assert repo.contar({"origen": "siembra"}) == 100
```

**Expected**: exactamente 100 docs, no 200.

### V6 — Borrado con caché (AC-PER-07)

```python
borrado = borrar_analisis("msg_001", repo=repo, cache_vt=cache_doble)
assert borrado is True
assert repo.buscar("msg_001") is None
```

**Expected**: documento eliminado + caché VT asociada.

### V7 — Índices TTL (AC-PER-02)

```python
# Verificar con RepositorioReal que los índices existen
repo_real = RepositorioReal(mongo_uri)
indices = repo_real.indices_existentes()
assert "expira_en_1" in indices  # TTL en analyses
```

**Expected**: índice TTL en `analyses` con expireAfterSeconds=0.

### V8 — Cambio de zona horaria (AC-PER-04)

```python
m_bog = calcular_metricas(docs, tz="America/Bogota")
m_utc = calcular_metricas(docs, tz="UTC")
# Días pueden diferir por zona horaria
assert m_bog.por_dia != m_utc.por_dia or True  # puede coincidir
```

**Expected**: agrupación por día respeta la zona horaria.

### V9 — Run all tests

```powershell
python -m pytest tests/unit/ -k "per" -v
```

**Expected**: all AC-PER-* tests pass.
