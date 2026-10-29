# Contrato: API pública de `src.level2_agent.virustotal` (fase 1)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Data model**: [data-model.md](../data-model.md)

La spec 006 es una **librería interna** dentro de `src/`: su interfaz externa es el
módulo Python que consumirán las specs 007 (scoring) y 008 (motor de decisión). No
expone endpoints HTTP (V.8 N/A). Este contrato fija firmas y garantías; el detalle de
tipos está en [data-model.md](../data-model.md).

## 1. Firma

```python
from src.level2_agent.virustotal import (
    ConfigVT, DependenciasVT, ResultadoVT, BanderaVT, Presupuesto,
    CATALOGO_VT, ConfiguracionError,
    consultar_archivo, consultar_url, consultar_dominio, consultar_ip,
    presupuesto_nuevo, clasificar_stats,
)

# API síncrona (D2): la asincronía interna (httpx.AsyncClient) queda encapsulada.
def consultar_archivo(sha256: str, *, config: ConfigVT | None = None,
                      deps: DependenciasVT | None = None,
                      presupuesto: Presupuesto | None = None) -> ResultadoVT: ...

def consultar_url(url: str, *, config: ConfigVT | None = None,
                  deps: DependenciasVT | None = None,
                  presupuesto: Presupuesto | None = None,
                  es_riesgosa: bool = False) -> ResultadoVT: ...

def consultar_dominio(dominio: str, *, config: ConfigVT | None = None,
                      deps: DependenciasVT | None = None,
                      presupuesto: Presupuesto | None = None) -> ResultadoVT: ...

def consultar_ip(ip: str, *, config: ConfigVT | None = None,
                 deps: DependenciasVT | None = None,
                 presupuesto: Presupuesto | None = None) -> ResultadoVT: ...

def presupuesto_nuevo(config: ConfigVT | None = None) -> Presupuesto: ...

def clasificar_stats(stats: LastAnalysisStats,
                     config: ConfigVT | None = None) -> Clasificacion: ...
```

- Todo con `**` tras el primer argumento → máximo 5 parámetros efectivos (III.2).
- `config=None` ⇒ `ConfigVT.desde_entorno()`; `deps=None` ⇒ `DependenciasVT` con
  `httpx.AsyncClient` real + caché/contador MongoDB (adaptadores) + reloj/jitter
  productivos. Ambos inyectables para pruebas (Art. II.5).
- `presupuesto=None` ⇒ la consulta **no** consume ficha de presupuesto (modo
  "consulta suelta", p. ej. pruebas); el wiring por correo (007/008) SIEMPRE pasa uno
  (`presupuesto_nuevo`) — es lo que garantiza FR-006.
- `es_riesgosa` marca la prioridad 2 (URL con banderas de riesgo media/alta de la
  004): la semántica de prioridad vive en el orden del wiring; el flag solo alimenta
  el `detalle` del presupuesto.

## 2. Entrada

| Parámetro | Tipo | Origen |
|---|---|---|
| `sha256` | `str` hex64 | `Adjunto.sha256` (spec 002) o `AnalisisAdjunto.sha256` (spec 005) |
| `url` | `str` | cruda o `ResultadoURLs.urls[].url_saneada` (spec 004); se sANA de nuevo aquí (D7) |
| `dominio` / `ip` | `str` | extraídos por el consumidor (007/008) |

## 3. Salida (`ResultadoVT`) — ejemplo canónico (AC-VT-01)

```json
{
  "tipo": "archivo",
  "identificador": "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f",
  "clasificacion": "maliciosa",
  "fuente": "red",
  "banderas": [{"codigo": "VT_ADJ_SOSPECHOSO", "severidad": "alta", "puntos": 25,
                "detalle": "hash de adjunto clasificado 'maliciosa' (malicious=5)"}],
  "stats": {"malicious": 5, "suspicious": 0, "harmless": 0, "undetected": 62},
  "consultas_externas": 1
}
```

Notas de contrato:

- `identificador` para URL: Base64 **url-safe sin relleno** (`base64.urlsafe_b64encode`
  sin `=`) — AC-VT-02; para archivo: SHA-256 en minúsculas.
- `puntos`/`severidad` salen de `CATALOGO_VT`, no se calculan (VI.2).
- `fuente="cache"` ⇒ `consultas_externas=0` (los golpes no consumen presupuesto).

## 4. Garantías (invariantes verificables)

| # | Garantía | Prueba |
|---|---|---|
| G1 | 404 ⇒ `desconocida` (+ `VT_DESCONOCIDO`), **jamás** `limpia` | `test_ac_vt_01_clasificacion.py` |
| G2 | Identificador de URL = Base64 url-safe sin `=`, `+`, `/` | `test_ac_vt_02_id_url.py` (+ property) |
| G3 | 5 consultas en `public` no exceden 4/min; 5.ª espera (o se omite si sin presupuesto); 500/día respetado tras reinicio | `test_ac_vt_03_cuota.py` |
| G4 | 429/5xx: ≤ 3 reintentos exponenciales 1/2/4 s, `Retry-After` respeta su valor; otros 4xx sin reintento | `test_ac_vt_04_reintentos.py` |
| G5 | 5 fallos ⇒ abierto 60 s sin llamadas ⇒ `VT_NO_DISPONIBLE`; tras la ventana, vuelve a cerrado | `test_ac_vt_05_cortacircuito.py` |
| G6 | Segunda consulta idéntica dentro del TTL ⇒ `fuente="cache"`, 0 llamadas HTTP | `test_ac_vt_06_cache.py` |
| G7 | Parámetros sensibles/PII fuera de toda petición; `VT_API_KEY` ausente de TODOS los logs | `test_ac_vt_07_saneado_clave.py` |
| G8 | Bordes de clasificación 2/3, 2/3, 19/20; presupuesto 10 → 10.ª consulta, 11.ª → `VT_PRESUPUESTO_AGOTADO` sin llamada | `test_ac_vt_08_limites.py` |
| G9 | `VT_UPLOAD_UNKNOWN=false` (default) ⇒ **cero** `POST` (el doble falla si lo ve) | `test_ac_vt_09_sin_subida.py` |
| G10 | EICAR por hash con respuesta grabada ⇒ `maliciosa`; sin EICAR en disco | `test_ac_vt_10_eicar.py` |
| G11 | Cero red real en pruebas (`MockTransport` + reloj/jitter/dormir inyectados) | conjunto (Art. II.5) |
| G12 | Ninguna entrada (hash malformado, URL gigante, IP inválida, sin `VT_API_KEY`) lanza excepción al consumidor | `test_ac_vt_01`/`test_ac_vt_07` |

## 5. Semántica de errores

| Situación | Comportamiento |
|---|---|
| 404 | `desconocida` + `VT_DESCONOCIDO`; con `submit_unknown_urls=false` ⇒ termina ahí sin POST (AC-VT-09) |
| 429 con/sin `Retry-After` | reintento ×3 con espera; si persiste ⇒ fallo para el cortacircuitos |
| 5xx | reintento ×3; si persiste ⇒ fallo para el cortacircuitos |
| Otros 4xx (400/401/403) | sin reintento; terminal ⇒ `desconocida` + `VT_DESCONOCIDO` |
| Timeout / error de transporte | fallo para el cortacircuitos ⇒ eventualmente `VT_NO_DISPONIBLE` |
| Cortacircuitos abierto | sin llamada ⇒ `desconocida` + `VT_NO_DISPONIBLE` (`fuente="sin_llamada"`) |
| Presupuesto agotado | sin llamada ⇒ `desconocida` + `VT_PRESUPUESTO_AGOTADO` (`fuente="sin_llamada"`) |
| Sin `VT_API_KEY` | sin intento de red ⇒ `desconocida` + `VT_NO_DISPONIBLE` |
| `config` inválida (ej. `VT_MAX_POR_CORREO=0`) | `ConfiguracionError` **al construir**, antes de consultar (III.9) |
| Indicador malformado (hash no-hex64, URL ingirable) | sin excepción; `desconocida` + `VT_DESCONOCIDO` (G12) |

**No hay** códigos HTTP: es una librería. El contrato HTTP/JSON de persistencia
pertenece a las specs 011/012 y consume `ResultadoVT` sin transformación de campos.

## 6. Puertos (interfaces de sustitución)

| Puerto | Método | Default prod | Sustituido en pruebas por |
|---|---|---|---|
| `ClienteHTTPVT` | `get(path) -> RespuestaVT` (`status`, `json`, `headers`) | `httpx.AsyncClient` + `Base_VT` (D2) | `httpx.MockTransport` con respuestas dictadas/JSON grabado |
| `RepositorioCacheVT` | `obtener(clave, ahora)`, `guardar(entrada)` | pymongo sobre `vt_cache` (índice TTL) | caché en memoria con reloj falso |
| `RepositorioContadorVT` | `consumir(dia) -> bool`, `usos(dia)` | pymongo sobre `vt_contador` (`$inc` atómico) | contador en memoria compartido (prueba de "reinicio" con dos instancias) |
| `Reloj` | `() -> datetime` (UTC) | `datetime.now(UTC)` | reloj falso avanzable |
| `Dormir` | `(segundos: float) -> None` | `asyncio.sleep` | captura de esperas en lista (cero espera real) |
| `Jitter` | `() -> float` | `random.uniform(0, 1)` | `lambda: 0.0` |

## 7. Compatibilidad

- Shape `BanderaVT` idéntico al de 003/004/005 (`codigo`/`severidad`/`puntos`/`detalle`)
  → concatenables en 007/008 sin adaptador.
- Sin wiring en esta spec (D14): las firmas usan `*` + defaults; en 007/008 se pueden
  **añadir** parámetros con default, nunca eliminar ni reordenar los existentes.
- `analisis_urls` y `adjuntos` intactos (006 solo los **importa**: `sanitizacion.py`
  en D7, y consume `sha256` como dato).
