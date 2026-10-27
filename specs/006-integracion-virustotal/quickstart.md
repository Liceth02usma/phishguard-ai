# Quickstart: Integración con VirusTotal API v3

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contrato**: [contracts/virustotal-api.md](./contracts/virustotal-api.md)

Guía de validación ejecutable de la spec 006. Sin código de implementación: solo
comandos y resultados esperados.

## 1. Previos

```powershell
# Ambiente (Windows, Python 3.11 local / 3.10+ requerido)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt     # incluye httpx (única dependencia nueva de la 006)

# .env — solo para corridas manuales con VT real (las pruebas NO lo leen)
#   VT_API_KEY=<clave>            # obligatoria solo si se consulta VT real
#   VT_TIER=public                # public | premium (public = SOLO DEMO — Art. V.7)
#   VT_RPM=4  VT_DAILY=500  VT_MAX_POR_CORREO=10   # defaults M06/tabla 14.x
#   VT_UPLOAD_UNKNOWN=false  VT_SUBMIT_UNKNOWN_URLS=false   # NUNCA true sin decisión documentada
#   VT_UMBRAL_MALICIOSA=3  VT_UMBRAL_SOSPECHOSA=3  VT_UMBRAL_LIMPIA=20   # M06.4
```

> La clave `VT_API_KEY` no debe aparecer en el repositorio, en logs ni en la salida de
> ningún comando de este guion (AC-VT-07).

## 2. Comando de validación principal

```powershell
# Compuerta completa (lint + tipos + tests + cobertura + trazabilidad AC) — Art. IV
python scripts/verify.py            # esperado: exit 0
```

Salida esperada (gates de la 006): `longitud_archivos`, `nombre_rama`, `cobertura`,
`trazabilidad_ac`, `secretos`, `lint`, `tipos` en PASS; `dependencias` puede quedar
como advertencia no bloqueante (entorno global, precedente de la 003).

```powershell
# Solo las pruebas de la spec (todas con dobles; cero red)
python -m pytest tests/unit -k "vt or clasificacion or limitador or cache_presupuesto" -v
# esperado: todos en verde, marcados con @pytest.mark.ac("AC-VT-01..10")

# Regresión del pipeline (no debe afectarse: D14 sin wiring)
python tests/test_pipeline.py       # esperado: exit 0 en los fixtures sanos
```

## 3. Escenarios de validación (qué prueba cada AC)

| # | Escenario | Comando / prueba | Resultado esperado |
|---|---|---|---|
| V1 | Clasificación y 404 | `pytest tests/unit/test_ac_vt_01_clasificacion.py` | `malicious=5` → `maliciosa`; 404 → `desconocida` + `VT_DESCONOCIDO`, nunca `limpia` (AC-VT-01) |
| V2 | Identificador de URL | `pytest tests/unit/test_ac_vt_02_id_url.py` | 3 URLs conocidas → Base64 url-safe sin `=`; propiedad `hypothesis` (AC-VT-02) |
| V3 | Cuota pública | `pytest tests/unit/test_ac_vt_03_cuota.py` | 5 consultas: 4.ª espera/omite (no hay 5.ª llamada en el minuto); 500.ª al día deja de llamar tras "reinicio" (AC-VT-03) |
| V4 | Reintentos | `pytest tests/unit/test_ac_vt_04_reintentos.py` | 429 con `Retry-After: 7` espera 7 s (no el exponencial); 429 sin header espera 1/2/4; 404 y 400 sin reintento (AC-VT-04) |
| V5 | Cortacircuitos | `pytest tests/unit/test_ac_vt_05_cortacircuito.py` | 5 fallos → 60 s sin llamadas → `VT_NO_DISPONIBLE`; a los 61 s vuelve a cerrado (AC-VT-05) |
| V6 | Caché | `pytest tests/unit/test_ac_vt_06_cache.py` | 2.ª consulta en TTL: `fuente="cache"`, 0 llamadas; expirada: 1 llamada nueva (AC-VT-06) |
| V7 | Saneado y secretos | `pytest tests/unit/test_ac_vt_07_saneado_clave.py` | URL con `token=`/`email=` sale sin ellos; caplog sin `VT_API_KEY` (AC-VT-07) |
| V8 | Valores límite | `pytest tests/unit/test_ac_vt_08_limites.py` | 2/3 malicious, 2/3 suspicious, 19/20 harmless+undetected; presupuesto 10/11 (AC-VT-08, SC-001/003) |
| V9 | Sin subida | `pytest tests/unit/test_ac_vt_09_sin_subida.py` | cero `POST` con default false; el doble falla si ve cualquier `POST` (AC-VT-09, Art. V.6) |
| V10 | EICAR integrado | `pytest tests/unit/test_ac_vt_10_eicar.py` | SHA-256 de EICAR (generado en memoria) + respuesta grabada → `maliciosa` (AC-VT-10) |
| V11 | Trazabilidad | `python scripts/check_trazabilidad_ac.py --spec specs/006-integracion-virustotal/spec.md` | AC-VT-01..10 todos con prueba |

## 4. Validación manual con VT real (opcional, requiere clave y red)

Solo con `VT_API_KEY` válida y aceptando la cuota pública (4/min). **No** es necesario
para el Art. IV (las pruebas son 100 % offline) y **no** forma parte de CI.

```powershell
python -c "from src.level2_agent.virustotal import consultar_archivo; \
r = consultar_archivo('275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f'); \
print(r.clasificacion, [b.codigo for b in r.banderas])"
# esperado (AC-VT-10): 'maliciosa' ['VT_ADJ_SOSPECHOSO']  — hash EICAR real de VT
# alternativa: un hash de un binario común → 'limpia' o 'desconocida' (404), nunca error
```

## 5. Verificación constitucional rápida (Art. VII.3)

| Comando | Resultado esperado |
|---|---|
| `python scripts/verify.py` | exit 0 (Art. IV.1a–f) |
| `git branch --show-current` | `feature/integracion-virustotal` (Art. I.2, regex del Art. I.1) |
| `grep -r "VT_API_KEY" logs/ 2>$null` | sin coincidencias (AC-VT-07, Art. V.3) |
| revisión: `git diff main --stat -- src/level2_agent/agent.py src/gmail_integration` | vacío (D14, Art. VI.1) |

## 6. Ítems `[VERIFICAR]` (no verificables desde este entorno — Art. VI.3)

| Ítem | Por qué | Dónde |
|---|---|---|
| Índice TTL real de Mongo (`expireAfterSeconds`) | no hay Mongo en CI | D3; probar en entorno con Atlas al hacer wiring 007/008 |
| Versión exacta de `httpx` instalable | depende del índice en el momento de fijar | `requirements.txt` (T000) |
| Cuota real 4/min y 500/día de VT | red + clave + términos del servicio | D5; solo demo manual §4 |
| `Retry-After` real de VT (segundos vs fecha) | respuesta del servidor no determinista | D6; el soporte de ambos formatos está cubierto por prueba con valor dictado |
| Latencia real (3 s conexión / 10 s lectura) | red pública | M06.3 |
