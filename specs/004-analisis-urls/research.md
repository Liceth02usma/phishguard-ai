# Research: Análisis y Expansión de URLs (fase 0)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Fecha**: 2026-10-22

Los campos `NEEDS CLARIFICATION` del plan y las dudas abiertas de la spec se resuelven
aquí con el formato **Decisión / Rationale / Alternativas consideradas** (Art. I del
workflow de `/speckit.plan`). Todo lo que no pudo verificarse contra spec/plan/código
queda marcado `[VERIFICAR]` en este documento y en `quickstart.md` (Art. VI.3).

## D1 — Dónde vive el código

**Decisión**: paquete nuevo `src/level2_agent/analisis_urls/` con módulos por fase
(extracción, normalización, banderas, saneo, SSRF, expansión) y un `motor.py` que
orquesta sin tocar el pipeline.

**Rationale**: consume `EmailData` (models.py, spec 002) y lo consumirán 006/007/008;
aislarlo permite TDD en paralelo con las specs 003/005 sin pisar archivos.

**Alternativas consideradas**: (a) extender `normalizacion/` — rechazada: 002 ya
convergió y su rama/árbol está en uso, otra responsabilidad; (b) `level3_logic` —
rechazado: ahí vive el genético, no reglas deterministas de URL; (c) módulo suelto
en `src/` — rechazado: rompe la estructura por nivel existente.

## D2 — Extracción propia vs reutilizar `normalizacion/extraccion.py`

**Decisión**: `analisis_urls/extraccion.py` propio: parsea `href`, `src`, `action`,
URLs de texto plano y de texto de enlaces, devolviendo **pares (texto_mostrado,
destino)** además de la lista de candidatas. `extraer_urls` de la 002 se deja intacta
(siguiendo poblando `EmailData.urls`).

**Rationale**: la bandera `URL_TEXTO_DISTINTO_DESTINO` (FR-002, AC-URL-01) exige
asociar el texto visible de cada enlace con su destino; `extraer_urls` solo devuelve
una lista `href`+regex, sin `src`/`action` ni pares. Modificarlo tocaría código
convergiado de 002 y sus tests en una rama paralela.

**Alternativas consideradas**: (a) ampliar `extraer_urls` y devolver pares — rechazada
por conflicto con 002 (VI.1: esta spec no refactoriza la 002); (b) guardar los pares
en `EmailData` — rechazada: cambiar `EmailData` exige edición de modelos + migración
de 002 y no lo pide la spec.

**Detalle**: se usa `html.parser.HTMLParser` de stdlib (sin dependencias nuevas, sin
JS — FR-005/AC-URL-04). `src`/`action` generan candidatas sin par texto (texto vacío).

## D3 — Modelo de bandera sin chocar con la spec 003 (paralela)

**Decisión**: `BanderaURL(codigo, severidad, puntos, detalle)` en
`analisis_urls/modelos.py`, con **los mismos nombres de campo** que `BanderaActivada`
de la spec 003. Sin imports entre ramas paralelas. La unificación de ambas listas en
un tipo único para el contrato (spec 011/007) queda para 007.

**Rationale**: 003 y 004 se desarrollan en paralelo; ambos editan `models.py` sería
conflicto de merge seguro. 003 ya decidió NO tocar `models.py`; 004 repite la
decisión. La coincidencia de campos garantiza que 007 pueda concatenar ambas listas
tal cual (contrato `analyses.resultado.banderas`).

**Alternativas consideradas**: (a) importar `BanderaActivada` desde
`level2_agent/banderas/` — rechazada: crea dependencia 004→003 y la spec 004 solo
depende de 002 (grafo de dependencias); (b) agregar `BanderaURL` a `models.py` —
rechazada: conflicto con 003.

**Aplicación del tope de 60 puntos** `[VERIFICAR → 007]`: el tope por correo de la
003 (AC-HDR-05) se aplica sobre las banderas de cabecera; el catálogo 5.2 no define
tope para las de URL y la 004 no lo pide. Esta spec emite **todas** las activadas y
007 unifica el tope global por correo. Si 003/004 se integran antes de 007, el
consumidor concatenado temporal puede superar 60 (documentado, no bloqueante).

## D4 — Caché de reputación de VT (FR-006) no existe todavía

**Decisión**: puerto `CacheReputacionURL` (`Protocol`) en `puertos.py` con contrato
`conoce(url_saneada) -> bool`. Implementación por defecto `CacheVacia` (siempre
`False` → se expande). La implementación real sobre `phishguard.vt_cache` llega con
las specs 006/011.

**Rationale**: FR-006 solo pide "no expandir si la reputación ya es conocida"; el
motor consume el puerto, por lo que la spec 004 es testeable hoy (doble con caché
llena/vacía) y 006/011 hacen el wiring sin reescribir el motor. `CacheVacia` expande
siempre = comportamiento correcto cuando no hay caché (no es degradación peligrosa:
la expansión está protegida por SSRF).

**Alternativas consideradas**: (a) leer `vt_cache` directamente del motor —
rechazada: acopla 004 a 006 (ciclo en el grafo) y rompe II.5 (dobles); (b) no
implementar FR-006 hasta 006 — rechazada: viola VI.1 (la FR pide el control hoy).

## D5 — `URL_DOMINIO_NUEVO` (RDAP) — la 003 lo implementa en paralelo

**Decisión**: puerto `ClienteRDAP` (`Protocol`) con `antiguedad_dias(dominio) ->
int | None`. Por defecto `SinRDAP` → `None` → **la bandera no se activa** (desconocido
≠ nuevo). La 003 construye además un Adapter RDAP con caché de 7 días; el wiring del
puerto de 004 con esa implementación se hace al integrar (007/008 o merge conjunto).

**Rationale**: mismo argumento que D4 — independencia de ramas, VI.1 (la bandera queda
implementada y probada con doble que devuelve 29/30/31 días) y V.1 (desconocido nunca
se reporta como "más de 30 días" ni como "nuevo", simplemente no emite).

**Alternativas consideradas**: (a) importar el cliente RDAP de `banderas/` (003) —
rechazada por D3; (b) duplicar la consulta RDAP dentro de 004 — rechazada: dos
clientes HTTP de RDAP para el mismo dato (DRY + V.3).

## D6 — Cliente HTTP para la expansión

**Decisión**: `requests` (ya en `requirements.txt`) con `allow_redirects=False`,
**manejo manual de saltos**, `HEAD` con fallback a `GET` en 405/501/403 y
`stream=True` para cerrar sin leer el cuerpo. Encapsulado tras el puerto
`ClienteHTTPExpansion` (una operación: `solicitar(url) -> RespuestaRedireccion`).
Cero dependencias nuevas.

**Rationale**: seguir redirecciones en automático haría imposible validar cada salto
(FR-004) y contar saltos/tiempo (FR-003); `requests` ya está fijado como dependencia;
`stream`+`close` cumple "sin descarga de cuerpos" (AC-URL-04).

**Alternativas consideradas**: (a) `httpx` — rechazada: dependencia nueva para algo
que `requests` resuelve (III.8); (b) `urllib` puro — rechazado: API cruda y manejo
manual de errores/métodos más propenso a fallos; (c) seguir `Location` con
`allow_redirects=True` — rechazado: imposibilita la validación SSRF por salto.

## D7 — Diseño del control SSRF (FR-004)

**Decisión**: en **cada petición** (primera o de redirección): (1) resolver el host
tras `ResolvedorDNS` (puerto; prod: `socket.getaddrinfo`); (2) validar **cada IP
resuelta** con `ipaddress` contra `REDES_PROHIBIDAS` (los CIDR exactos de FR-004)
**y** contra `is_global == False` (art. V.5: cubre además `0.0.0.0/8`, multicast y
reservadas que FR-004 enumera como "lista"); (3) solo si todas pasan, conectar.
Las IPs se revalidan dentro del cliente antes de abrir la conexión (doble chequeo).

**Rationale**: la regla literal de FR-004 es "privadas, de enlace local, loopback o
de metadatos de nube"; `is_global` da esa cobertura con menos superficie de error
que listar rangos a mano, y la lista exacta se mantiene además como defensa en
profundidad legible. La ventana entre validar y conectar (TOCTOU con reconfiguración
de DNS) es de milisegundos y se documenta; el pinning total de IP (conectar a la IP
validada conservando Host/SNI) queda `[VERIFICAR]` como mejora si la spec 006/008
lo exige.

**Alternativas consideradas**: (a) solo la lista de FR-004 — rechazada: deja fuera
`0.0.0.0/8` y multicast; (b) solo `is_global` — rechazada: la lista explícita es más
legible y es lo que el auditor busca; (c) pinning de IP en `requests` — descartada
por coste/soporte (marcada como mejora `[VERIFICAR]`).

**Rangos → bandera/estado**: cualquier IP bloqueada produce
`ResultadoExpansion.estado = "bloqueada_ssrf"` y la bandera de la URL correspondiente
(que es la del propio acortador, p. ej. `URL_ACORTADA`); **jamás se intenta la
conexión** (AC-URL-02: servidor local de prueba recibe cero peticiones cuando el
primer salto resuelve a privada).

## D8 — Listas y umbrales no numéricos de la spec

**Decisión** (todo configurable por `.env`, con defaults documentados y
`[VERIFICAR]` donde la fuente es una propuesta, no la spec):

| Config | Fuente del default | Estado |
|---|---|---|
| `ACORTADORES` | `SHORTENERS` existente de `genetic_logic.py` (`bit.ly`, `tinyurl`, `goo.gl`, `t.co`) | grounded en código |
| `TLD_RIESGO` | propuesta corta: `.zip`, `.mov`, `.tk`, `.ml`, `.cf`, `.ga`, `.gq` | `[VERIFICAR]` (plan: "TLD de riesgo configurable", sin lista) |
| `PARAMETROS_TRACKING` | `utm_*`, `fbclid`, `gclid`, `msclkid`, `igshid`, `mc_eid`, `ref` | `[VERIFICAR]` (plan: "parámetros de seguimiento conocidos", sin lista) |
| `URL_SUBDOMINIOS_MAX` | propuesta: 4 etiquetas fuera del dominio registrable | `[VERIFICAR]` (plan: "subdominios excesivos", sin umbral) |
| `URL_PUERTO_NO_ESTANDAR` | puerto presente distinto de 80/443 | grounded en plan ("puerto no estándar") |

**Rationale**: el plan califica estas listas de "configurable"; 003 resolvió igual
(listas por env con defaults documentados). Los valores que sí son numéricos y
explícitos (5 saltos, 5 s, 200 caracteres, 30 días) NO se hacen configurables sin
decisión — salen literalmente de FR-003/M04b.

**Alternativas consideradas**: (a) listas fijas en código — rechazadas: el plan pide
configurables; (b) defaults vacíos — rechazados: `URL_TLD_RIESGO`/`URL_ACORTADA`
nunca dispararían (bandera muerta por defecto).

## D9 — Semántica de `REDIRECCION_EXCESIVA` (AC-URL-03: 4, 5 y 6 saltos)

**Decisión**: la expansión hace **como máximo 5 peticiones** (`TOPE_SALTOS = 5`) y
corta a los 5 s (`TIMEOUT_URL_SEGUNDOS = 5`). `REDIRECCION_EXCESIVA` se activa
cuando la expansión termina **sin destino final** por uno de esos dos límites:

| Cadena del servidor | Resultado | Bandera |
|---|---|---|
| 4 redirecciones y luego 200/3xx final no-acortador | `expandida`, destino final | no |
| 5.ª respuesta sigue siendo redirección | se detiene en el salto 5 | **sí** |
| 6+ redirecciones (nunca hay 6.ª petición) | se detiene en el salto 5 | **sí** |
| 5.ª redirección pendiente pero ya pasaron 5 s | se detiene por tiempo | **sí** |

**Rationale**: SC-003 dice "se detiene en 5 saltos o 5 s y registra
REDIRECCION_EXCESIVA"; con tope 5, "probar 6 saltos" = probar que **jamás** hay una
6.ª petición. 4 saltos = expansión completa y limpia.

**Alternativas consideradas**: (a) activar la bandera solo a partir de 6 —
rechazada: inalcanzable con tope 5 (la bandera nunca se activaría); (b) activar en
cualquier redirección >1 — rechazada: contradice SC-003.

## D10 — Técnicas de prueba (Art. II.2: ≥ 3, valor límite y tabla obligatorias)

**Decisión — 6 técnicas**:

1. **Valores límite** (obligatoria): 4/5/6 saltos, 4.9/5.0/5.1 s, 200/201 caracteres,
   29/30/31 días (RDAP), umbral de subdominios, URL de 100 000 caracteres,
   puertos 80/443/otro.
2. **Tabla de decisión** (obligatoria): (i) máquina de estados de expansión
   (¿acortadora? ¿caché la conoce? ¿esquema? ¿IP válida? ¿saltos? ¿tiempo? →
   estado); (ii) matriz SSRF: cada red de FR-004 + pública → permitida/bloqueada.
3. **Partición de equivalencia**: familias de banderas (positivo/negativo por
   código: 13 códigos × casos), tipos de URL (malformada vs válida, IPv4/IPv6/host).
4. **Propiedades con `hypothesis`** (ya fijada): (a) AC-URL-06 — para cualquier URL
   de entrada, la que sale del límite de consulta externa no contiene valores de
   `token`/`password` ni strings con forma de correo; (b) AC-URL-07 — para cualquier
   cadena arbitraria, `analizar_urls` no lanza excepción.
5. **Integración con dobles + servidor local**: servidor `http.server` de loopback
   (context manager) para redirecciones y conteo de peticiones/cuerpos; dobles de
   DNS (mapping dominio→IP de prueba) y del cliente HTTP (secuencias de respuestas).
6. **Regresión**: `tests/test_pipeline.py` debe seguir en PASS (nada cambia en el
   flujo actual).

**Rationale**: obligatorias (II.2) las dos primeras; las 6 cubren seguridad (SSRF),
PII (saneador), determinismo (reloj falso) y estados de degradación.

## D11 — Sin wiring al pipeline

**Decisión**: `agent.py`, `prompts.py`, `gmail_poller.py` y `models.py` sin cambios;
`motor.analizar_urls` no se invoca en el flujo actual. El wiring lo harán 006 (VT
sobre URLs), 007 (scoring con banderas de URL) y 008 (decisión).

**Rationale**: precedente directo de la spec 003 (su D11), mismo grafo de
dependencias y misma rama paralela; la spec pide el módulo, no su conexión.

**Alternativas consideradas**: cablear ya en `analyze_email` — rechazada: rompería
AC de 006/007 (no implementados aún) y el pipeline actual en verde.

## D12 — PII: qué puede salir de la spec

**Decisión**: toda URL que cruza el límite de **consulta externa** (expansión; VT en
006) pasa antes por `sanitizar_parametros()` (FR-007): elimina los parámetros
sensibles **textuales de la FR-007** (`token`, `key`, `session`, `email`, `user`,
`code`, `password`) y los valores con forma de correo/TLD de correo (AC-URL-06).
Los `detalle` de banderas
cit host, puerto y **nombres** de parámetros, jamás valores ni correos. El análisis
interno (extracción, banderas `URL_PARAMETROS_SENSIBLES`) trabaja sobre la URL
completa porque no sale del proceso.

**Rationale**: V.4 (PII antes de persistir/enviar a terceros) + VI.2 (el saneador no
inventa política: la spec define los 7 nombres y "valores con forma de correo"; la
lista es extensible por env pero su default es literalmente FR-007).

**Alternativas consideradas**: sanitizar desde la extracción — rechazada: perderíamos
la señal de `URL_PARAMETROS_SENSIBLES` (que necesita ver los nombres) y alteraríamos
la URL "original" que el reporte debe conservar (FR-001).

## D13 — Presupuesto de expansión

**Decisión**: expansión **solo** de hosts de la lista de acortadores (subconjunto
escaso), secuencial, ≤ 5 s por URL; el límite de 200 URLs de la spec 002 acota el
peor caso. Sin concurrencia (YAGNI).

**Rationale**: el plan solo fija "5 s por URL"; paralelizar añade complejidad y
violación de determinismo de orden. Peor caso teórico (200 acortadores × 5 s) queda
documentado; `[VERIFICAR]` si la demo algún día alimenta 200 acortadores reales.

**Alternativas consideradas**: hilos/async — rechazados por III.5/YAGNI y porque
"misma entrada → mismo orden de resultados" es más fácil de probar secuencial.

## D14 — Coordinación con ramas paralelas (003/005/015)

**Decisión**: archivos compartidos **solo ediciones aditivas**, una línea por spec:
`scripts/verify.py` (+ `--cov=` y + `RUTAS_CALIDAD_SRC`), `pyproject.toml`
(+ override mypy), `tests/unit/conftest.py` (+ fixtures propios), `.env.example`
(+ 4 vars), `README.md`/`AGENTS.md` (+ nota M04b). Conflictos de merge se resuelven
secuencialmente al integrar (resolución trivial: conservar ambas líneas).

**Rationale**: el directorio de trabajo está compartido por sesiones paralelas (ya se
observaron ramas y artefactos de 003/005/015 apareciendo durante este plan).

**Alternativas consideradas**: esperar a converger 003/005 — rechazada: el usuario
pidió paralelismo (003+004+005+015 en paralelo tras 002).

## D15 — Reloj inyectado (determinismo de los 5 s)

**Decisión**: `DependenciasURLs.reloj: Callable[[], float]` sobre `time.monotonic`
en producción; en pruebas, reloj falso avanzable. El límite de tiempo se mide en el
motor de expansión (comparando lecturas de reloj), no con `time.sleep`.

**Rationale**: II.5 prohíbe depender del tiempo real; un timeout de 5 s con reloj real
haría la prueba lenta y no determinista (máquina lenta → falso negativo).

**Alternativas consideradas**: `pytest-timeout`/espera real — rechazadas: prueba lenta
y no determinista; `unittest.mock.patch` del tiempo — aceptada como mecanismo, pero
el puerto explícito es más simple y tipable.

## Resumen de `NEEDS CLARIFICATION` resueltos

| Original en plan/spec | Resuelto en |
|---|---|
| Cliente HTTP de expansión | D6 (`requests` manual, 0 deps) |
| Forma de validar IPs por salto | D7 (lista FR-004 + `is_global`, doble chequeo) |
| Caché VT (FR-006) inexistente | D4 (puerto + `CacheVacia`) |
| RDAP de `URL_DOMINIO_NUEVO` (003 paralela) | D5 (puerto + `SinRDAP`) |
| Listas configurables sin defaults | D8 (defaults documentados, `[VERIFICAR]`) |
| Semántica 4/5/6 saltos | D9 (tabla) |
| Duplicación de extracción con 002 | D2 |
| Conflicto de modelo de bandera con 003 | D3 |
| Quién aplica el tope de 60 puntos | D3 `[VERIFICAR → 007]` |
| TOCTOU del cliente HTTP | D7 `[VERIFICAR]` |
| Peor caso 200 acortadores | D13 `[VERIFICAR]` |
