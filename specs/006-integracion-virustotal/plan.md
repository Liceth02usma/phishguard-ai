# Implementation Plan: Integración con VirusTotal API v3

**Branch**: `feature/integracion-virustotal` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-integracion-virustotal/spec.md`

## Summary

Construir un cliente determinista de VirusTotal API v3 en `src/level2_agent/virustotal/`
(11 módulos) que clasifique archivos por SHA-256, URLs (identificador Base64 url-safe sin
relleno), dominios e IPs leyendo `last_analysis_stats` con una **tabla de decisión** de
umbrales configurables (FR-007); con **limitador de cubeta** `public` 4/min y 500/día
(contador diario persistente, FR-002), **reintentos** en 429/5xx (hasta 3, exponencial
1/2/4 s + jitter inyectable, respetando `Retry-After`, FR-003), **cortacircuitos** (5
fallos consecutivos → abierto 60 s → `VT_NO_DISPONIBLE`, FR-004), **caché Repository**
con TTL por tipo (archivos 7 días; URL/dominio/IP 24 h; desconocido 1 h, FR-005) y
**presupuesto por correo** de 10 consultas con prioridad hashes → URLs con banderas →
dominios → IPs → demás URLs (`VT_PRESUPUESTO_AGOTADO`, FR-006). Un 404 es
`desconocida`, nunca `limpia` (FR-001); la subida de archivos y el envío de URLs
desactivados por defecto (`VT_UPLOAD_UNKNOWN=false`, `VT_SUBMIT_UNKNOWN_URLS=false`,
FR-008); `VT_API_KEY` solo por entorno y jamás en logs (FR-009, AC-VT-07).

Cliente `httpx.AsyncClient` (M06.3) con transporte simulado `httpx.MockTransport` en
pruebas; API pública síncrona porque los consumidores (specs 007/008) son síncronos.
Caché y contador diario tras puertos `Protocol` con implementación MongoDB (pymongo,
ya presente) e implementación en memoria para pruebas (Art. II.5: sin red real).
**Una dependencia nueva** (`httpx`, fijada y auditada). Sin wiring al pipeline
(precedente D11 de las specs 003/004/005): `agent.py`, `prompts.py`, el poller e
`ip_reputation.py` quedan intactos; consumidoras = 007/008. 6 técnicas de prueba
(valor límite y tabla de decisión, ambas obligatorias, más contrato con respuestas
grabadas, dobles, propiedades con `hypothesis` y regresión), trazabilidad AC-VT-01..10
y compuertas de `verify.py` extendidas al paquete nuevo.

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10)

**Primary Dependencies**: `httpx` (única dependencia nueva, fijada; M06.3 exige
`httpx.AsyncClient` y su `MockTransport` da transporte simulado deterministic), `pydantic`
y `pymongo` (ambos ya en `requirements.txt`); stdlib `asyncio`, `base64`, `logging`,
`re`, `datetime`; tooling: pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks;
`hypothesis` (ya fijada) para propiedades del saneado y del clasificador

**Storage**: MongoDB (colección `vt_cache` con índice TTL sobre `expira_en` y colección
`vt_contador` para el tope diario persistente — M06.3); en pruebas, implementaciones en
memoria con reloj inyectado (nunca Mongo real en CI)

**Testing**: pytest con `@pytest.mark.ac("AC-VT-NN")`; tabla de decisión sobre el
clasificador FR-007 y sobre la máquina de estados del cortacircuitos; valores límite
(2/3 malicious, 2/3 suspicious, 19/20 harmless+undetected, presupuesto 10/11, 4/min,
5 fallos, 60 s, TTLs); `httpx.MockTransport` con respuestas grabadas (AC-VT-01/10),
cero red externa (Art. II.5), `--cov --cov-branch` sobre `scripts/` y el paquete nuevo;
ruff y `mypy --strict` sobre el código nuevo

**Target Platform**: Windows local + Linux CI (GitHub Actions)

**Project Type**: librería dentro de `src/` (paquete `virustotal`) consumida por las
specs 007 (scoring) y 008 (motor de decisión); sin endpoint ni binario propio

**Performance Goals**: consultas con timeout de conexión 3 s y lectura 10 s (M06.3);
consultas en paralelo (`asyncio.gather`) respetando el limitador; caché hit sin E/S
externa; el cortacircuitos evita picos cuando VT cae

**Constraints**: determinismo — reloj y jitter inyectados, misma entrada +
configuración + respuestas → mismo resultado; secretos solo por entorno, jamás en logs
(AC-VT-07); ningún `.py` > 500 líneas (objetivo 300); funciones ≤ 40 líneas y ≤ 5
parámetros; `mypy --strict` (Art. III.4); el modo `public` es solo demostración —
prohibición comercial documentada (FR-002, Art. V.7)

**Scale/Scope**: ~11 módulos nuevos en `src/level2_agent/virustotal/`, ~14 archivos de
prueba en `tests/unit/`, 5 códigos de catálogo (`VT_URL_SOSPECHOSA`,
`VT_ADJ_SOSPECHOSO`, `VT_DESCONOCIDO`, `VT_NO_DISPONIBLE`, `VT_PRESUPUESTO_AGOTADO`),
1 dependencia nueva (`httpx`); ediciones **aditivas** y compartidas con las ramas de
las specs 007/008 en `scripts/verify.py`, `pyproject.toml`, `tests/unit/conftest.py`,
`.env.example`, `requirements.txt`, `README.md` y `AGENTS.md`; **sin** cambios en
`agent.py`, `prompts.py`, el poller, `normalizacion/`, `analisis_urls/` ni `adjuntos/`
(research D11/D12)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS | `feature/integracion-virustotal` creada desde `main` (d413417, con las specs 004 y 005 ya mergeadas — la 006 depende de ambas) **antes** que cualquier artefacto de planificación de esta sesión; cumple la regex del Art. I.2 |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | Commits `feat\|test\|docs: … (AC-VT-NN)` solo en la rama; `main` no recibe commits directos |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase TDD dedicada en tasks.md; el rojo se confirma contra un paquete inexistente |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 6 técnicas en `research.md` D11: valores límite (obligatorio: 2/3, 2/3, 19/20, 10/11, 4/min, 5 fallos, 60 s, TTL), tabla de decisión (obligatorio: clasificador FR-007 y máquina de estados del cortacircuitos), contrato con respuestas grabadas (AC-VT-01/10), integración con dobles (rate limit, caché, presupuesto), propiedades con `hypothesis` (identificador Base64 y saneado), regresión (`test_pipeline.py` verde) |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | `verify.py` y `pyproject.toml` se EXTENDEN para medir `src/level2_agent/virustotal/` (mismo mecanismo D10 de las specs 002/003/004/005: ampliar alcance, no bajar umbrales) |
| II.4 | Sin pruebas sin `assert` | PASS | Toda prueba verifica clasificación observada, llamadas HTTP realizadas/no realizadas, estados del cortacircuitos, golpes de caché o flags emitidos |
| II.5 | Sin red real ni hora sin controlar | PASS | Cliente HTTP tras `httpx.MockTransport` (respuestas grabadas/dictadas); caché y contador con implementación en memoria y reloj inyectado; jitter y esperas tras callables inyectados (cero `time.sleep` real en pruebas) |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-VT-01..10")`; verificado con `scripts/check_trazabilidad_ac.py --spec specs/006-integracion-virustotal/spec.md` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica ninguna prueba existente; `fail_under` no baja |
| III.1 | Archivos `.py` ≤ 500 líneas (objetivo 300) | PASS | 11 módulos por responsabilidad; el mayor (`cliente.py`) ≈ 370 líneas; los flujos tras flags viven en `envios.py` para respetar el límite |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | La entrada común se agrupa en `ConfigVT` + `DependenciasVT` + `Presupuesto` (Art. III.2); el clasificador y el saneador son funciones puras de 1–3 parámetros |
| III.3 | `snake_case` en español sin tildes | PASS | `consultar_archivo`, `clasificar_stats`, `limitador`, `cortacircuito`, `TOPE_CONSULTAS_DIA=500`, `UMBRAL_MALICIOSA=3` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict` ampliado al paquete nuevo; `ResultadoVT`/`BanderaVT`/`ConfigVT` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Adapter (cliente HTTP httpx sobre puerto, Repository caché/contador MongoDB), Repository (`RepositorioCacheVT`, `RepositorioContadorVT`), Circuit Breaker (M06.3 lo nombra), Strategy/Tabla de decisión (clasificador FR-007), inyección de dependencias — nombrados en `research.md` D1/D3/D5/D6/D8; nada más |
| III.6 | Sin números ni cadenas mágicas | PASS | 4/min, 500/día, 3 reintentos, 1/2/4 s, 5 fallos, 60 s, TTL 7 d/24 h/1 h, 10/correo, 3 s/10 s, umbrales 3/3/20 y catálogo VT como constantes nombradas; `VT_*` como configuración con defaults documentados en research D9 |
| III.7 | Una responsabilidad por módulo | PASS | Un módulo por mecanismo: limitador, reintentos/cortacircuitos, caché, presupuesto, clasificación, saneado/identificadores, cliente; el `__init__` solo expone |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | `httpx` fijado con versión exacta y pasado por `pip-audit`; ruff/mypy sobre el paquete nuevo |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` vacíos: caídas, 429, 5xx, 404, cuota y cortacircuitos se MODELAN como estados de `ResultadoVT` (`desconocida` + flags); error propio `ConfiguracionError`; AC-VT-01/05 garantizan que ninguna entrada lanza excepción hacia el consumidor |
| IV.1a–i | Definición de terminado | PASS | `verify.py` exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar | PASS | `desconocida` nunca cuenta como `limpia` (FR-001/AC-VT-01); `VT_NO_DISPONIBLE`/`VT_DESCONOCIDO`/`VT_PRESUPUESTO_AGOTADO` son informativas que **obligan** a `revision_manual` (catálogo 5.2, interpretado por 008); "limpia" no reduce el score (M06.4) |
| V.2 | Acciones externas por código determinista, DRY_RUN por defecto | PASS | El cliente solo LEE reputación; las dos acciones con efecto externo (subir archivo, enviar URL a análisis) están tras flags `VT_UPLOAD_UNKNOWN`/`VT_SUBMIT_UNKNOWN_URLS` **en false por defecto** (FR-008, AC-VT-09) y requieren decisión documentada |
| V.3 | Secretos fuera de reposo | PASS | `VT_API_KEY` solo por variable de entorno; jamás en logs ni en mensajes de error (AC-VT-07 con prueba que intercepta el logger) |
| V.4 | PII enmascarada antes de persistir/enviar a terceros | PASS | Las URLs se sanean **antes** de cualquier consulta: reutiliza `sanitizacion.py` de la spec 004 (parámetros sensibles + valores con forma de correo, FR-007/AC-URL-06 de la 004) — research D7; los `detalle` de banderas citan tipo/identificador saneado, nunca la URL original con tokens |
| V.5 | Adjuntos en memoria; SSRF validado en cada salto | PASS (con nota) | No se siguen enlaces ni se resuelven hosts: las consultas van a `https://www.virustotal.com/api/v3` (host fijo, sin destino controlado por el usuario — mismo argumento del saneado RDAP de la spec 003); el identificador de URL se compone solo tras el saneador; la subida de archivos está desactivada por defecto (V.2) |
| V.6 | Sin envío de archivos a terceros por defecto | PASS | **Núcleo del Art. V.6**: solo se consulta por hash (SHA-256 calculado localmente); `POST /files` no se emite jamás con `VT_UPLOAD_UNKNOWN=false` (AC-VT-09 lo prueba con el cliente simulado) |
| V.7 | Uso permitido de API externa (VT pública solo demo) | PASS | `VT_TIER=public|premium` configurable sin cambio de lógica (FR-002); la restricción comercial queda documentada en plan/spec/`.env.example` y en el docstring de `ConfigVT`; decisión Premium para producción = del equipo (fuera de alcance) |
| V.8 | API con X-API-Key única, sin roles | N/A | Esta spec no expone endpoints HTTP |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-009; fuera: veredicto (008), scoring (007), retiro de `ip_reputation.py` del agente (pertenece a la spec del agente, M07) y wiring en `agent.py`/poller |
| VI.2 | No inventar valores | PASS | 4/min, 500/día, 3 reintentos, 1/2/4 s, 5 fallos, 60 s, TTLs, 10/correo, 3 s/10 s, umbrales 3/3/20, endpoints, nombres `VT_*` de env y códigos de catálogo salen textualmente de M06.1–M06.4, de la tabla de variables (14.x) y de los catálogos 5.2/5.3; los nombres de las env vars de umbrales (`VT_UMBRAL_*`) no existen en el plan maestro — FR-007 pide "umbrales configurables" y sus nombres se documentan como decisión en `research.md` D9 |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Quedan `[VERIFICAR]`: índice TTL real de MongoDB, comportamiento real de la cuota de VT, versión exacta de `httpx` disponible en el entorno, latencia del `Retry-After` real (marcados en quickstart) |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procedió a research.

**Re-evaluación post-fase 1** (tras `research.md`, `data-model.md`,
`contracts/virustotal-api.md`, `quickstart.md`): SIN violaciones nuevas.

- **I**: rama `feature/integracion-virustotal` creada desde `main` con 004+005
  mergeadas (dependencias de la 006 verificadas con `merge-base --is-ancestor`).
- **II.2**: 6 técnicas documentadas en D11 (valor límite y tabla de decisión, ambas
  obligatorias, cubiertas por el clasificador D4 y el cortacircuitos D6).
- **II.5**: `httpx.MockTransport` + reloj/jitter/caché/contador inyectados (D2/D3/D5);
  cero `sleep` real y cero socket real en pruebas.
- **V.1/V.6/V.7**: `desconocida` ≠ `limpia`, subida en false por defecto con prueba
  negativa (AC-VT-09) y `public` documentado como solo-demo (D8).
- **V.4**: saneado reutilizando la spec 004 antes de toda red (D7); la clave no
  aparece en logs con prueba que intercepta el logger (D10).
- **VI.2/VI.3**: constantes textuales del M06 en `data-model.md`; nombres de env vars
  de umbrales y semántica half-open marcados como decisiones (D9/D6) y `[VERIFICAR]`
  en el quickstart.

## Project Structure

### Documentation (this feature)

```text
specs/006-integracion-virustotal/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── virustotal-api.md  # Phase 1 output (API pública del paquete virustotal)
├── checklists/
│   └── requirements.md    # checklist de requirements (16/16 PASS)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── models.py                    # SIN CAMBIOS (EmailData y Adjunto ya traen hashes/urls)
│   ├── agent.py                     # SIN CAMBIOS (wiring de 007/008 — D11)
│   ├── prompts.py                   # SIN CAMBIOS
│   ├── tools/ip_reputation.py       # SIN CAMBIOS (su retiro es de la spec del agente, M07)
│   ├── analisis_urls/               # SIN CAMBIOS (solo se importa su saneador, D7)
│   ├── adjuntos/                    # SIN CAMBIOS (solo se consume su sha256, D12)
│   └── virustotal/                  # NUEVO paquete (FR-001..FR-009)
│       ├── __init__.py              #   API pública: consultar_archivo/consultar_url/
│       │                            #   consultar_dominio/consultar_ip, presupuesto_nuevo,
│       │                            #   ConfigVT, DependenciasVT, ResultadoVT, BanderaVT, CATALOGO_VT
│       ├── modelos.py               #   Clasificacion, BanderaVT, ResultadoVT, CATALOGO_VT (5 códigos),
│       │                            #   constantes (TOPE_RPM_PUBLIC=4, TOPE_DIA_PUBLIC=500, REINTENTOS_MAX=3,
│       │                            #   ESPERA_BASE_SEGUNDOS=1, FALLOS_CORTACIRCUITO=5, VENTANA_CORTACIRCUITO_SEGUNDOS=60,
│       │                            #   TTLs, TIMEOUT_CONEXION_SEGUNDOS=3.0, TIMEOUT_LECTURA_SEGUNDOS=10.0)
│       ├── configuracion.py         #   ConfigVT desde env (VT_TIER, VT_RPM, VT_DAILY, VT_MAX_POR_CORREO,
│       │                            #   VT_UPLOAD_UNKNOWN, VT_SUBMIT_UNKNOWN_URLS, VT_UMBRAL_*) + ConfiguracionError
│       ├── puertos.py               #   Protocol: ClienteHTTPVT (httpx.AsyncClient), Reloj, Dormir,
│       │                            #   RepositorioCacheVT, RepositorioContadorVT + DependenciasVT
│       ├── identificadores.py       #   id_url_base64 (url-safe sin relleno, AC-VT-02), sanitizar_url (D7)
│       ├── clasificacion.py         #   clasificar_stats(): tabla de decisión FR-007 (AC-VT-08)
│       ├── limitador.py             #   cubeta 4/min (proceso) + contador diario persistente (AC-VT-03)
│       ├── resiliencia.py           #   reintentos 429/5xx con Retry-After + cortacircuitos 5/60 s (AC-VT-04/05)
│       ├── cache.py                 #   Repository TTL por tipo (archivos 7 d; URL/dominio/IP 24 h; 404 1 h, AC-VT-06)
│       ├── presupuesto.py           #   presupuesto por correo (10, prioridad, VT_PRESUPUESTO_AGOTADO, FR-006)
│       ├── cliente.py               #   orquestador: endpoint + clasificación + flags (AC-VT-01/07/10)
│       ├── envios.py                #   POST /files y /urls SOLO tras VT_UPLOAD_UNKNOWN /
│       │                            #   VT_SUBMIT_UNKNOWN_URLS (AC-VT-09, FR-008); verify.py NO se toca

tests/
├── unit/
│   ├── conftest.py                  # EDITAR (aditivo): fixtures VT (config de prueba, dobles)
│   ├── dobles_vt.py                 # NUEVO: httpx.MockTransport con respuestas por endpoint,
│   │                                #   reloj falso, dormir falso (lista de esperas), caché/contador en memoria
│   ├── respuestas_vt/               # NUEVO (carpeta): respuestas grabadas/anonimizadas en JSON
│   │                                #   (NUNCA tests/fixtures/ — eso rompería test_pipeline.py, D12)
│   ├── test_ac_vt_01_clasificacion.py   # NUEVO (malicious=5 → maliciosa; 404 → desconocida)
│   ├── test_ac_vt_02_id_url.py          # NUEVO (3 URLs conocidas + property hypothesis)
│   ├── test_ac_vt_03_cuota.py           # NUEVO (4/min, quinta espera; 500/día tras "reinicio")
│   ├── test_ac_vt_04_reintentos.py      # NUEVO (429 con/sin Retry-After; 5xx; 404 sin reintento)
│   ├── test_ac_vt_05_cortacircuito.py   # NUEVO (5 fallos → abierto 60 s → VT_NO_DISPONIBLE)
│   ├── test_ac_vt_06_cache.py           # NUEVO (segunda consulta dentro del TTL sin llamada)
│   ├── test_ac_vt_07_saneado_clave.py   # NUEVO (parámetros sensibles fuera; clave ausente en logs)
│   ├── test_ac_vt_08_limites.py         # NUEVO (2/3, 2/3, 19/20) + presupuesto 10/11
│   ├── test_ac_vt_09_sin_subida.py      # NUEVO (cero POST con VT_UPLOAD_UNKNOWN=false)
│   ├── test_ac_vt_10_eicar.py           # NUEVO (hash EICAR + respuesta grabada → maliciosa)
│   ├── test_clasificacion.py            # NUEVO (tabla de decisión completa FR-007)
│   ├── test_limitador.py                # NUEVO (cubeta con reloj falso; contador diario)
│   └── test_cache_presupuesto.py        # NUEVO (TTLs por tipo; orden de prioridad)
├── test_pipeline.py                 # SIN CAMBIOS (regresión: debe seguir verde)
└── fixtures/                        # SIN CAMBIOS (los JSON de VT van en tests/unit/respuestas_vt/, D12)

scripts/
└── verify.py                        # EDITAR (aditivo): --cov=src/level2_agent/virustotal y
                                     # RUTAS_CALIDAD_SRC incluye el paquete (compartido con 007/008)

pyproject.toml               # EDITAR (aditivo): mypy override estricto para virustotal.*
tests/unit/conftest.py       # EDITAR (aditivo): autouse para reiniciar estado de proceso (cortacircuitos)
.env.example                 # EDITAR (aditivo): VT_TIER, VT_RPM, VT_DAILY, VT_MAX_POR_CORREO,
                             # VT_UPLOAD_UNKNOWN, VT_SUBMIT_UNKNOWN_URLS, VT_UMBRAL_* (sin la clave)
requirements.txt             # EDITAR: httpx==<versión fijada> (única dependencia nueva)
README.md                    # EDITAR (aditivo): módulo M06 y comando de pruebas
AGENTS.md                    # EDITAR (aditivo): nota del paquete virustotal/
```

**Structure Decision**: se conserva la estructura existente; el cliente vive en un
paquete nuevo dentro de `level2_agent/` porque consume `EmailData`/`Adjunto` (spec 002),
`sanitizacion.py` (spec 004, D7) y el `sha256` de `analizar_adjunto` (spec 005), y las
specs 007/008 lo consumirán desde ahí. El plan maestro lo llama
`src/enrichment/virustotal.py` (M06.3), pero los módulos M03/M04b/M05 ya habitaron en
`level2_agent/` (precedente unánime de las specs 002–005) y un solo archivo violaría el
Art. III.1 (el cliente con limitador, cortacircuitos, caché, presupuesto y clasificador
superaría 500 líneas) — misma desviación de ruta justificada que en las specs previas,
sin cambio funcional. Cada mecanismo es un módulo de funciones puras o classes pequeñas
(Strategy/Adapter/Repository/Circuit Breaker, `research.md` D1/D3/D6). El paquete **no**
se conecta al pipeline en esta spec (D11, precedente de las specs 003/004/005): el
alcance es producir un cliente verificable de forma independiente. Las compuertas de la
spec 000 se EXTENDEN al paquete nuevo (mismo mecanismo de las 002–005): sin eso el
código nuevo quedaría sin medir y violaría II.3/III.4.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS
> y N/A; la dependencia nueva `httpx` no es una violación — M06.3 la exige y se fija
> con versión exacta + `pip-audit`).
