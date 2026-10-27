# Research: Integración con VirusTotal API v3

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Fecha**: 2026-10-27

Resolución de las preguntas abiertas del *Technical Context* y de los puntos que la
spec/plan dejan como configurable. Cada decisión usa el formato
**Decisión / Razón / Alternativas descartadas**. Los valores de dominio (cuotas,
umbrales, TTL, endpoints) NO se inventan: salen de M06.1–M06.4 de
`docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, de la tabla de variables (14.x) o de los
catálogos 5.2/5.3; lo que es lista configurable se marca como tal.

## D1 — Ubicación del código

**Decisión**: paquete nuevo `src/level2_agent/virustotal/` (10 módulos), importado como
`src.level2_agent.virustotal`, con `EmailData`/`Adjunto` (spec 002) como datos de entrada.

**Razón**: M06.3 nombra `src/enrichment/virustotal.py`, pero los módulos M03/M04b/M05
viven en `level2_agent/` (precedente unánime de las specs 002–005), las consumidoras
007/008 lo invocarán desde esa capa, y un archivo único con limitador + cortacircuitos +
caché + presupuesto + clasificador superaría las 500 líneas del Art. III.1. Mismo
tratamiento que la ruta `src/enrichment/` recibió en las specs previas: desviación de
ruta sin cambio funcional, documentada.

**Alternativas descartadas**: (a) `src/enrichment/virustotal.py` literal — un archivo
grande viola III.1 y crea una capa nueva sin consumidoras; (b) adentro de
`analisis_urls/` — acopla 006 a 004 (ciclo: 004 ya define un puerto `CacheReputacionURL`
para 006) y mezcla E/S de red con lógica pura de URLs; (c) `tools/` junto a
`ip_reputation.py` — heredaría el patrón `StructuredTool` del agente que esta spec no
modifica (VI.1).

## D2 — httpx síncrono vs asíncrono y transporte simulado

**Decisión**: `httpx.AsyncClient` con timeouts de conexión 3 s y lectura 10 s (M06.3),
envuelto por una **API pública síncrona** (`asyncio.run` interno). Las consultas de un
correo se paralelizan con `asyncio.gather` respetando el limitador. En pruebas, el
transporte se sustituye por `httpx.MockTransport` (respuestas dictadas o leídas de JSON
grabado) — cero sockets.

**Razón**: M06.3 exige `httpx.AsyncClient` y "consultas en paralelo respetando el
limitador"; las consumidoras (007/008, `analyze_email`) son síncronas, así que la
asyncronidad se encapsula y no contamina el contrato. `MockTransport` es el doble
oficial de httpx: determinista, en memoria, sin red (Art. II.5).

**Alternativas descartadas**: (a) `requests` síncrono (lo usa hoy `ip_reputation.py`) —
sin paralelismo viola M06.3 y con él la premisa de "máx. 4/min se agotan menos"; (b)
`aiohttp` — librería extra no citada por el plan; (c) servidor local de loopback como
en la spec 004 — innecesario: aquí no se prueban saltos SSRF sino respuestas VT.

## D3 — Caché y contador diario: Repository con dos implementaciones

**Decisión**: puertos `Protocol` `RepositorioCacheVT` (`obtener(clave) -> EntradaCache |
None` / `guardar(EntradaCache)`) y `RepositorioContadorVT` (`consumir(dia) -> bool`).
Producción: adaptadores pymongo sobre `vt_cache` (índice TTL sobre `expira_en`) y
`vt_contador` (documento `{_id: "YYYY-MM-DD", usos: n}` — sobrevive reinicios, M06.3).
Pruebas y default de proceso sin Mongo: implementaciones en memoria con reloj
inyectado. La spec no inyecta repo → `DependenciasVT` los agrupa (Art. III.2).

**Razón**: FR-005 exige MongoDB y el contador debe persistir reinicios, pero Art. II.5
prohibe red real en CI (no hay Mongo en el CI; las specs 003/004/005 nunca tocaron red).
El patrón Repository (Art. III.5) separa la semántica de TTL/presupuesto (probada en
memoria, con reloj falso) de la E/S de Mongo (adaptador fino, `[VERIFICAR]` su índice
TTL real en el quickstart).

**Alternativas descartadas**: (a) caché en proceso como la RDAP de la 003 — viola
FR-005 (Mongo explícito) y el contador no sobreviviría reinicios (AC-VT-03 lo pide);
(b) mongomock en pruebas — dependencia nueva y frágil, además de probar pymongo, no la
lógica; (c) TTL solo como campo `expira_en` consultado por la app sin índice — se deja
el índice como `[VERIFICAR]` pero el filtrado por fecha es el contrato funcional.

## D4 — Clasificador FR-007 como tabla de decisión pura

**Decisión**: `clasificar_stats(stats: LastAnalysisStats, config: UmbralesVT) ->
Literal["maliciosa", "sospechosa", "limpia", "desconocida"]`, función pura que solo lee
`malicious`, `suspicious`, `harmless`, `undetected`. Reglas literales M06.4:
`malicious >= umbral_maliciosa (3)` → maliciosa; `malicious ∈ [1,2]` o
`suspicious >= umbral_sospechosa (3)` → sospechosa; `malicious == 0` y
`suspicious <= 2` y `harmless + undetected >= umbral_limpia (20)` → limpia; cualquier
otro caso → desconocida. Los tres umbrales son configurables (FR-007: "los umbrales son
configurables"). Un diccionario vacío o sin `last_analysis_stats` → `desconocida`
(nunca limpia). 404/error/cuota agotada → `desconocida` en el cliente (no pasa por la
tabla).

**Razón**: Art. II.2 marca la tabla de decisión como obligatoria cuando hay reglas con
varias condiciones — FR-007 lo es. Separarla en una función pura la hace testeable con
particiones y valores límite sin HTTP (AC-VT-08). "Limpia" nunca reduce el score:
el efecto lo da 007/008, aquí solo se clasifica (VI.1).

**Alternativas descartadas**: (a) clasificar en `cliente.py` junto al HTTP — no
separable para la tabla de decisión; (b) inferir por `engine_detection` en vez de
`last_analysis_stats` — M06.4 fija `last_analysis_stats`.

## D5 — Limitador de cubeta: 4/min por proceso + 500/día persistente

**Decisión**: cubeta de 4 fichas por ventana de 60 s **por proceso** (en memoria,
reloj inyectado) + contador diario consultado al `RepositorioContadorVT` (persistente).
`VT_TIER=public` aplica 4/min y `VT_DAILY` (default 500; 0 = sin tope); `premium`
ignora el tope diario fijo y usa `VT_RPM` (M06.3: "valor configurable"). Antes de cada
llamada externa: si no hay ficha diaria → sin llamada (resultado `desconocida` +
`VT_PRESUPUESTO_AGOTADO` no aplica aquí: la cuota diaria agotada produce
`VT_NO_DISPONIBLE`… ver D6b). Si no hay ficha de minuto → el llamador espera (dormir
inyectable, no `sleep` real en pruebas) o, si el presupuesto del correo se agotó, omite
(AC-VT-03: "la quinta espera u se omite").

**Razón**: M06.3 fija "cubeta de fichas por proceso: public = 4/min y 500/día
(contador persistente en MongoDB para sobrevivir reinicios)". El reloj inyectado
mantiene determinismo (Art. II.5). El "espera u omite" de AC-VT-03 se resuelve a favor
de **esperar** cuando queda presupuesto (la espera usa el reloj/dormir inyectados) y de
**omitir** cuando el presupuesto por correo ya se agotó (D8).

**D5b — semántica del tope diario agotado**: sin ficha diaria el cliente no llama y
devuelve `desconocida` con `VT_NO_DISPONIBLE` (no `VT_PRESUPUESTO_AGOTADO`, que es
exclusivo del presupuesto por correo, FR-006/M06.3).

**Alternativas descartadas**: (a) solo en memoria — AC-VT-03 exige "tras un reinicio",
lo que obliga persistencia real (Mongo); (b) `aiolimit`/`token-bucket` de librería —
dependencia nueva para 20 líneas con reloj inyectado; (c) sleep real — rompe II.5.

## D6 — Reintentos y cortacircuitos

**Decisión** (`resiliencia.py`): (a) **reintentos**: en 429 y 5xx hasta 3 intentos
extras con espera exponencial `ESPERA_BASE_SEGUNDOS=1 → 2 → 4` más jitter positivo
inyectable (`Callable[[], float]`, default `random.uniform(0, 1)` — en pruebas se pasa
`lambda: 0.0`); si la respuesta trae `Retry-After` (segundos o fecha HTTP) se respeta
**ese** valor en lugar del exponencial. 404 y demás 4xx: sin reintento (el 404 es
resultado, no error). (b) **cortacircuitos**: 5 fallos consecutivos (cualquier error de
transporte, 5xx o 429 tras agotar reintentos) abren la ventana de 60 s; durante la
ventana no se realiza ninguna llamada y el resultado es `desconocida` +
`VT_NO_DISPONIBLE`. El contador de fallos se restablece a 0 con una respuesta 200 o
404. Estado en proceso (módulo con `dataclass`), reloj inyectado.

**Razón**: M06.3 fija 3 reintentos, 1/2/4 s, `Retry-After`, 5 fallos y 60 s; Art. II.2
obliga tabla de decisión — la máquina `cerrado → abierto → cerrado` (con 200/404 como
reset) es una transición de estados testeable con reloj falso. "La analización continúa
con `VT_NO_DISPONIBLE`" (AC-VT-05) ⇒ el cortacircuitos nunca lanza excepción.

**D6b — sin half-open**: M06.3 no menciona estado de prueba (half-open): al vencer los
60 s el cortacircuitos vuelve a cerrado. Se documenta para no inventar comportamiento
(VI.2); si M13/calibración lo pide, será una ampliación futura.

**Alternativas descartadas**: (a) reintento en todo 4xx — M06.3 lo prohíbe
expresamente (excepto 429); (b) jitter fijo 0 — M06.3 exige "más aleatoriedad" (la
inyección lo hace determinista en pruebas sin negar la aleatoriedad en producción);
(c) librería `tenacity`/`circuitbreaker` — dependencia nueva para reglas de 15 líneas.

## D7 — Saneado de URLs: reutilizar la spec 004

**Decisión**: `identificadores.sanitizar_url(url)` delega en
`src.level2_agent.analisis_urls.sanitizacion.sanitizar_parametros()` (y en la limpieza
de valores con forma de correo que la 004 ya implementa, FR-007/AC-URL-06 de aquella
spec) **antes** de componer el identificador Base64 y antes de cualquier petición.
Además, `DetalleBandera`/logs citan solo host + nombres de parámetro.

**Razón**: AC-VT-07 ("los parámetros sensibles se eliminan de la URL antes de
consultar") es exactamente la garantía I3 de la 004; duplicar el saneador crearía dos
fuentes de verdad (riesgo de divergencia). Importar el módulo de 004 no crea ciclo: 004
no importa 006 (su `CacheReputacionURL` es un puerto con `CacheVacia`).

**Alternativas descartadas**: (a) saneador propio en 006 — duplica lógica ya probada
con `hypothesis` en la 004; (b) no sanear y confiar en que 004 ya lo hizo — la API de
006 es pública y puede recibir URLs crudas (los consumidores 007/008 podrían llamarla
con cualquier entrada); la defensa en profundidad es barata.

## D8 — Presupuesto por correo con prioridad

**Decisión**: objeto `Presupuesto` (dataclass) creado por `presupuesto_nuevo(config)`,
con `restantes` (default `VT_MAX_POR_CORREO=10`), `usar() -> bool` y
`agotado: bool`. El cliente consulta a través de él: cada llamada externa (no los
golpes de caché) consume 1 ficha; `usar() == False` ⇒ sin llamada y bandera
`VT_PRESUPUESTO_AGOTADO` (informativa, 0 puntos). Orden de prioridad (M06.3 literal):
1) hashes de adjuntos, 2) URLs con banderas de riesgo de severidad media/alta,
3) dominios, 4) IPs, 5) demás URLs. El consumidor (006 wiring futuro/007/008) itera en
ese orden; la función de consumo acepta la prioridad como el orden en que se invoca.
Los golpes de caché **no** consumen presupuesto (FR-006: "consultas externas").

**Razón**: FR-006/M06.3 fijan 10, el orden y la bandera; AC-VT-08 pide los bordes
exactos 10 y 11. Mantener el presupuesto fuera del cliente (objeto aparte) permite que
varias consultas de un mismo correo compartan fichas sin estado global (Art. II.5: sin
orden implícito entre pruebas).

**Alternativas descartadas**: (a) contador global por proceso — no es "por correo"
(FR-006) y contaminaría pruebas; (b) que el cliente asigne prioridad solo — la
prioridad es decisión de quién arma la lista de consultas (el wiring futuro), 006 solo
garantiza el orden documentado como contrato.

## D9 — Configuración: env vars del plan + umbrales

**Decisión**: `ConfigVT.desde_entorno()` lee las vars **literales** de la tabla 14.x:
`VT_TIER` (default `public`), `VT_RPM` (4), `VT_DAILY` (500), `VT_MAX_POR_CORREO` (10),
`VT_UPLOAD_UNKNOWN` (false), `VT_SUBMIT_UNKNOWN_URLS` (false). Los umbrales de
FR-007 no tienen nombre en el plan; se les asigna `VT_UMBRAL_MALICIOSA` (3),
`VT_UMBRAL_SOSPECHOSA` (3), `VT_UMBRAL_LIMPIA` (20) — valores literales de M06.4,
nombres marcados como decisión propia (VI.2: se documentan, no se inventan valores).
`VT_API_KEY` se lee en el cliente **solo** para la cabecera `x-apikey`, jamás se loguea
(AC-VT-07). Valor inválido (tier distinto de public/premium, negativo, no numérico) →
`ConfiguracionError` al construir (III.9). Las listas no llevan defaults propios.

**Razón**: la tabla 14.x es fuente literal para 6 vars; FR-007 exige umbrales
configurables y sus valores (3, 3, 20) están en M06.4 ("los umbrales (3, 3, 20) son
propuestas; se calibran con M13"). `VT_UPLOAD_UNKNOWN`/`VT_SUBMIT_UNKNOWN_URLS`
default false = Art. V.6.

**Alternativas descartadas**: (a) umbrales hardcodeados — FR-007 pide configurables;
(b) `pydantic-settings` para leer env — el proyecto usa `ConfigX.desde_entorno()` con
`os.getenv` (precedente 003/004/005); cambiar de mecanismo rompería consistencia.

## D10 — Logging y secretos (AC-VT-07)

**Decisión**: un único `logger = logging.getLogger("src.level2_agent.virustotal")`.
Los mensajes citan tipo + identificador **ya saneado** y códigos HTTP; jamás la clave,
ni la URL original con parámetros, ni el header `x-apikey` (que se construye dentro de
la función de petición y no se materializa en variables externas). Prueba: interceptor
de `logging` (caplog) que recorre todos los mensajes de una corrida completa con clave
ficticia `VT_API_KEY=supersecreta` y afirma que no aparece.

**Razón**: AC-VT-07 + Art. V.3/V.4. El patrón de "construir la cabecera donde se usa"
reduce la ventana de fuga accidental.

**Alternativas descartadas**: (a) maskado por regex en el formatter — más complejo y
propenso a olvidos; (b) no usar logging — ilegible para operación.

## D11 — Técnicas de prueba (Art. II.2: mínimo 3, obligatorias cuando apliquen)

**Decisión**: 6 técnicas:

| Técnica | Uso en esta spec |
|---|---|
| **valores límite** (obligatoria) | AC-VT-08: `malicious` 2/3, `suspicious` 2/3, `harmless+undetected` 19/20; presupuesto 10/11; 4 fichas + 5.ª; 5.º fallo (cortacircuitos) y 59/60 s de ventana; TTL justo antes/expirado (7 d, 24 h, 1 h) |
| **tabla de decisión** (obligatoria) | `clasificar_stats` (todas las filas de M06.4) y máquina de estados `cerrado → abierto → cerrado` del cortacircuitos con 200/404/5xx/429 |
| contrato con respuestas grabadas | `respuestas_vt/*.json` anónimas para AC-VT-01 (200 maliciosa, 404) y AC-VT-10 (EICAR) vía `httpx.MockTransport` |
| integración con dobles | rate limit (reloj falso), caché/contador (memoria), reintentos (`Retry-After`), presupuesto, cero `POST` (AC-VT-09) |
| propiedades (`hypothesis`) | AC-VT-02: `id_url_base64` es url-safe sin `=`, sin `+`/`/`, idempotente y reinyectable; saneado nunca lanza |
| regresión | `tests/test_pipeline.py` debe seguir verde (no se toca el pipeline) |

**Razón**: el Art. II.2 las enumera y exige justificación; las dos obligatorias
aplican (umbrales numéricos + reglas con varias condiciones).

**Alternativas descartadas**: fakes de servidor local (innecesarios: no hay cadenas de
redirección aquí, a diferencia de la 004); pruebas contra VT real (prohibidas por II.5
y por la cuota pública).

## D12 — EICAR y fixtures: dónde viven las respuestas grabadas

**Decisión**: las respuestas VT grabadas van en `tests/unit/respuestas_vt/*.json`
(anonimizadas: se eliminan ids internos y datos de la cuenta). El vector EICAR se
**genera en memoria** reutilizando `tests/unit/vector_eicar.py` (spec 005): su SHA-256
se calcula con `hashlib` en el propio test (o se importa `EICAR_SHA256` de 005) y se
dicta la respuesta grabada correspondiente al `MockTransport`. **Nunca** se escribe en
`tests/fixtures/`.

**Razón**: `tests/test_pipeline.py` globera *todo* `*.json` de `tests/fixtures/` como
fixture de pipeline — un JSON de VT rompería la regresión (lección documentada en
AGENTS.md). AC-VT-10 pide "respuesta grabada", no red real. SC-003 de la 005 (EICAR sin
disco) se respeta: solo bytes en memoria.

**Alternativas descartadas**: (a) fixtures en `tests/fixtures/` — rompe
`test_pipeline.py`; (b) diccionarios inline en el test — aceptable para casos mínimos,
pero los cuerpos VT son grandes y 10 ACs los comparten; (c) descargar VT real — red,
cuota y no determinista (II.5).

## D13 — Subida de archivos y envío de URLs (FR-008)

**Decisión**: las funciones `subir_archivo()` y `enviar_url_desconocida()` existen en
`cliente.py` pero **cortan antes de construir la petición** cuando
`VT_UPLOAD_UNKNOWN=false` / `VT_SUBMIT_UNKNOWN_URLS=false` (defaults) y devuelven
`None`/estado documentado sin llamada. `enviar_url_desconocida` solo se invoca como
parte del flujo 404-de-URL y, aun habilitado, está limitado a 3 consultas de
`GET /analyses/{id}` espaciadas 5 s (M06.2). Con el flag en false (default) el flujo
404 termina en `desconocida` sin POST (AC-VT-09 con cliente simulado que falla si ve
cualquier `POST`).

**Razón**: FR-008 + Art. V.2/V.6: "desactivados por defecto" ⇒ el código debe poder
habilitarse por decisión documentada (no quedarse sin implementar, que sería un
`missing` futuro), pero la ruta por defecto no emite `POST` jamás (AC-VT-09).

**Alternativas descartadas**: (a) no implementar la subida (solo el flag) — rompería
FR-008 cuando el equipo decida habilitarla y M06.2 la lista como endpoint a usar;
(b) implementarla activa por defecto — viola Art. V.6 y M06.1/AC-VT-09.

## D14 — Wiring y consumidores (precedente D11 de 003/004/005)

**Decisión**: sin cambios en `agent.py`, `prompts.py`, el poller ni
`ip_reputation.py`. La spec 006 produce el paquete verificable de forma independiente;
el consumo (adjuntos + URLs → 007 scoring → 008 veredicto) lo harán las specs 007/008,
y el retiro de la tool `ip_reputation.py` pertenece a la spec del agente (M07). El
contrato `virustotal-api.md` fija firmas con defaults para que el wiring futuro sea
adicional.

**Razón**: precedente unánime 003/004/005 (D11), VI.1 (solo lo que pide la spec), y
evita conflictos entre ramas paralelas sobre `agent.py`.

**Alternativas descartadas**: wiring inmediato en `analyze_email` — rompería la
regresión de la 001 (LLM prose-vs-JSON ya frágil, verificado en la 003) y mezclaría
alcances.

## D15 — Concurrencia y determinismo del `gather`

**Decisión**: las consultas de un mismo correo se lanzan con `asyncio.gather` pero
**adquiriendo el limitador en orden** (la cubeta se toma en el event loop, sin
`await` entre comprobar y consumir la ficha: sección crítica síncrona de un solo
thread). El resultado se ordena según la lista de entrada (no según el orden de
finalización), de modo que misma entrada + mismas respuestas → mismo `ResultadoVT`.

**Razón**: M06.3 exige "consultas en paralelo respetando el limitador"; Art. II.5
exige determinismo — el orden de finalización de `gather` es no determinista si las
respuestas tardan distinto, por eso se reordena.

**Alternativas descartadas**: (a) serializar todo (sin `gather`) — pierde el paralelismo
que exige M06.3; (b) confiar en el orden de `gather` — `gather` preserva el orden de
la lista de entrada en los resultados (se verifica con un doble de latencias distintas
para no depender del supuesto).

## Riesgos residuales

| Riesgo | Mitigación |
|---|---|
| Índice TTL real de Mongo no probado en CI | Adaptador fino + `[VERIFICAR]` en quickstart (D3) |
| Cuota pública real agota durante demos | Cortacircuitos + caché + `VT_NO_DISPONIBLE` → `revision_manual` (D5/D6) |
| Uso comercial con clave gratuita | `VT_TIER` documentado + aviso en `.env.example` y docstring (Art. V.7) |
| Divergencia de saneado con 004 | Delegación directa, no duplicado (D7) |
| `httpx` no disponible en el entorno | Se fija versión exacta en `requirements.txt` y se verifica instalación en T000 |
