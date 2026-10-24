# Contrato: API pública de `src.level2_agent.analisis_urls` (fase 1)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Data model**: [data-model.md](./data-model.md)

La spec 004 es una **librería interna** dentro de `src/`: su interfaz externa es el
módulo Python que consumirán las specs 006 (VT sobre URLs), 007 (scoring) y 008
(decisión). No expone endpoints HTTP (V.8 N/A). Este contrato fija la firma y las
garantías; el detalle de tipos está en [data-model.md](./data-model.md).

## 1. Firma

```python
from src.level2_agent.models import EmailData
from src.level2_agent.analisis_urls import (
    ConfigURLs, DependenciasURLs, ResultadoURLs, analizar_urls,
    ConfiguracionError, dependencias_por_defecto,
)

def analizar_urls(
    email_data: EmailData,
    config: ConfigURLs | None = None,      # None → ConfigURLs.desde_entorno()
    deps: DependenciasURLs | None = None,  # None → dependencias_por_defecto()
) -> ResultadoURLs: ...
```

3 parámetros (Art. III.2: la E/S se agrupa en `DependenciasURLs`, research D4–D7/D15).
`config=None` ⇒ configuración desde entorno con defaults documentados (D8);
`deps=None` ⇒ implementaciones de producción (DNS/`requests`/caché vacía/sin RDAP).

## 2. Entrada

| Parámetro | Tipo | Origen |
|---|---|---|
| `email_data` | `EmailData` | spec 002 (sin cambios). Se usan `htmlBody`, `texto_limpio` y `textBody`. |
| `config` | `ConfigURLs` | D8 (listas configurables) |
| `deps` | `DependenciasURLs` | puertos para pruebas/producción |

## 3. Salida (`ResultadoURLs`)

Ejemplo canónico (AC-URL-01 + AC-URL-02 combinados):

```json
{
  "urls": [
    {
      "original": "https://bit.ly/3xAb?utm_source=mail&token=abc123&email=j.perez@banco.com",
      "normalizada": "https://bit.ly/3xAb?token=abc123&email=j.perez@banco.com",
      "host": "bit.ly",
      "esquema": "https",
      "texto_mostrado": "https://banco.com",
      "es_acortadora": true,
      "url_saneada": "https://bit.ly/3xAb",
      "codigos": ["URL_TEXTO_DISTINTO_DESTINO", "URL_ACORTADA"],
      "expansion": {
        "estado": "bloqueada_ssrf",
        "destino_final": null,
        "saltos": 1,
        "duracion_ms": 12,
        "motivo": "ip_bloqueada: 127.0.0.1"
      }
    }
  ],
  "banderas": [
    {"codigo": "URL_TEXTO_DISTINTO_DESTINO", "severidad": "alta", "puntos": 20,
     "detalle": "texto 'https://banco.com' ≠ destino 'bit.ly'"},
    {"codigo": "URL_ACORTADA", "severidad": "media", "puntos": 10,
     "detalle": "host acortador: bit.ly"}
  ],
  "estadisticas": {"total": 1, "expandidas": 0, "bloqueadas_ssrf": 1, "sin_expansion": 0}
}
```

Notas del ejemplo (y son contrato):

- `original` conserva tracking y PII para el reporte interno (FR-001); `url_saneada`
  es lo único que sale a red (FR-007, AC-URL-06: aquí `token` y `email` eliminados).
- `puntos`/`severidad` salen del catálogo 5.2, no se calculan (VI.2).
- `expansion.estado = "bloqueada_ssrf"` con `saltos >= 1`: la 1.ª petición fue a un
  host de prueba cuya IP resuelta era loopback → **cero conexiones** (AC-URL-02).

## 4. Garantías (invariantes verificables)

| # | Garantía | Prueba |
|---|---|---|
| I1 | Cero conexión a redes de FR-004 (primer salto o tras redirección) | `test_ac_url_02_ssrf_privados.py`, `test_ssrf.py` |
| I2 | Ningún cuerpo de respuesta se descarga (`ya_leido == False`) | `test_ac_url_04_sin_cuerpo.py` |
| I3 | La URL que cruza a cualquier puerto externo pasa antes por el saneador | `test_ac_url_06_saneado.py` (propiedad `hypothesis`) |
| I4 | Deduplicación tras normalizar, preservando `original` y orden | `test_ac_url_05_dedup.py` |
| I5 | `codigo ∈ catálogo 5.2` (13 códigos); puntos copiados, no inventados | `test_banderas_url.py` (tabla) |
| I6 | Ninguna entrada (vacía, malformada, 100 000 caracteres) lanza excepción | `test_ac_url_07_malformadas.py` |
| I7 | ≤ 5 peticiones por URL; sin JavaScript; resultados deterministas con reloj falso | `test_ac_url_03_limite_saltos.py`, `test_expansion.py` |

## 5. Semántica de errores

| Situación | Comportamiento |
|---|---|
| URL malformada/vacía/sin host | sin excepción; `ResultadoExpansion.error_controlado` o URL simplemente no analizable (`urls` la incluye con `host=""`, I6) |
| DNS/conexión/timeout/4xx/5xx | `error_controlado` (nunca propaga `requests`/`socket`) |
| IP prohibida | `bloqueada_ssrf`, 0 conexiones (I1) |
| Caché VT o RDAP ausentes | estados `reputacion_conocida`/sin bandera — degradación explícita, jamás "seguro" (V.1, D4/D5) |
| `config` inválida (ej. `URL_SUBDOMINIOS_MAX=abc`) | `ConfiguracionError` al construir, antes de analizar (III.9) |
| Fallo inesperado interno | se propaga como excepción **solo** si rompe I6; cualquier fuga es bug (AC-URL-07) |

**No hay** códigos HTTP: es una librería. El contrato HTTP/JSON de resultados (banderas
en `analyses.resultado.banderas`) pertenece a las specs 011/012 y consume esta salida
sin transformación de campos (D3).

## 6. Puertos (interfaces de sustitución)

| Puerto | Método | Default prod | Sustituido en pruebas por |
|---|---|---|---|
| `ResolvedorDNS` | `resolver(host) -> list[IP]` | `socket.getaddrinfo` | doble con mapping host→IP (`dobles_red.py`) |
| `ClienteHTTPExpansion` | `solicitar(url) -> RespuestaRedireccion` | adapter `requests` (D6) | doble con secuencia de respuestas / servidor local |
| `CacheReputacionURL` | `conoce(url) -> bool` | `CacheVacia` → `False` | doble lleno/vacío (FR-006) |
| `ClienteRDAP` | `antiguedad_dias(dominio) -> int \| None` | `SinRDAP` → `None` | doble 29/30/31 días (`URL_DOMINIO_NUEVO`) |
| reloj | `() -> float` | `time.monotonic` | reloj falso avanzable (D15) |

## 7. Compatibilidad

- Campo `banderas` con `codigo`/`severidad`/`puntos`/`detalle` = shape del contrato
  REST 012 (`analyses.resultado.banderas`) y de las banderas de 003 → concatenables
  en 007 sin adaptador (D3).
- Sin wiring en esta spec (D11): la firma puede afilarse en 006/007/008 solo con
  cambios compatibles (parámetros por defecto), nunca eliminando `analizar_urls`.
- `models.py` intacto (D3): `EmailData` sigue siendo el único tipo de entrada.
