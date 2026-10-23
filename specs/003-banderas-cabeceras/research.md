# Research: Banderas Deterministas de Cabeceras y Remitente

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Fecha**: 2026-10-22

Resolución de las preguntas abiertas del *Technical Context* y de los puntos que la
spec deja como "configurable" o como hint de diseño. Cada decisión usa el formato
**Decisión / Razón / Alternativas descartadas**. Los valores de dominio (puntos,
severidades, umbrales) NO se inventan: salen del catálogo 5.1, del módulo M03 o de la
spec (Art. VI.2); lo que es lista configurable se marca como tal.

## D1 — Ubicación del código

**Decisión**: paquete nuevo `src/level2_agent/banderas/` (9 módulos), importado como
`src.level2_agent.banderas`, con `EmailData` de `src.level2_agent.models` como entrada.

**Razón**: espejo exacto de `normalizacion/` (spec 002): misma capa, mismas
convenciones, misma vida útil (las specs 007/008 consumirán el resultado desde el
mismo nivel). `EmailData.cabeceras` ya conserva el orden físico de las cabeceras y los
valores RFC 2047 decodificados, que es justo lo que M03 necesita.

**Alternativas descartadas**: dentro de `normalizacion/` (rol distinto: aquello sanea,
esto juzga identidad); `src/banderas/` de nivel superior (rompe la cohesión con
`models.py` y con los consumidores level2).

## D2 — Patrón de diseño

**Decisión**: **Strategy** (una clase/estrategia por bandera, interfaz común
`Protocol` con `codigo: str` y `evaluar(ctx) -> BanderaActivada | None`) + **Registry**
(lista ordenada de estrategias, orden = orden del catálogo 5.1) + **Adapter**
(`ClienteRDAP` como protocolo; implementación real con `requests`).

**Razón**: Art. III.5 los nombra como candidatos previstos (Strategy para reglas,
Adapter para RDAP). La spec lo pide explícitamente en su hint. Además AC-HDR-01 exige
un par positivo/negativo **por bandera**: la estrategia 1:1 con la bandera hace que
cada prueba mapee a una unidad de código pequeña y trazable.

**Alternativas descartadas**: una función gigante con if/else por bandera (estalla el
límite de 500 líneas del Art. III.1 y hace imposible la trazabilidad AC→código);
motor de reglas externo (dependencia nueva, YAGNI).

## D3 — Estructura de módulos por familia

**Decisión**: `modelos.py` (modelos públicos + catálogo), `configuracion.py` (env),
`autenticacion.py` (4 banderas de autenticación), `identidad.py` (5 banderas de
remitente), `dominios.py` (2 banderas de dominio + utilidades puras), `contexto.py`
(3 banderas de contexto), `rdap.py` (adapter + 2 banderas de edad), `motor.py`
(registry + tope de puntos), `__init__.py` (API pública).

**Razón**: cada módulo queda < 200 líneas estimadas (Art. III.1 objetivo 300) y una
responsabilidad clara (Art. III.7). Las familias coinciden con las del catálogo 5.1.

**Alternativas descartadas**: un archivo por bandera (16 archivos de ~30 líneas:
excesivo, dispersión); un solo archivo `banderas.py` (superaría el límite con los
tests).

## D4 — Parsing de `Authentication-Results` (RFC 8601) y `authserv-id`

**Decisión**: parser propio, puro y pequeño (stdlib, sin dependencia): por cada
cabecera `Authentication-Results`, extraer el `authserv-id` (primer token, con
comentarios `(...)` y CFWS eliminados) y las parejas `método=resultado`. Se confía
**solo** en las cabeceras cuyo `authserv-id` coincide, exacta e insensible a
mayúsculas, con el configurado. Para cada método, el primer resultado de una cabecera
de confianza gana (recorrido en orden físico, de arriba hacia abajo). Reglas del
catálogo 5.1: `SPF_FALLA` si spf ∈ {fail, softfail}; `DKIM_FALLA` si dkim = fail;
`DMARC_FALLA` si dmarc = fail; `AUTH_NO_EVALUABLE` **solo** cuando no existe ninguna
cabecera de confianza (lectura literal de la regla "Sin Authentication-Results
confiable"). Los métodos ausentes en una cabecera de confianza quedan
`desconocido` en los estados sin activar bandera (el catálogo no define bandera ni
puntos para ello: no se inventan, Art. VI.2). `permerror`/`temperror` se registran en
`estados_autenticacion` pero tampoco suman puntos (mismo motivo).

**Razón**: AC-HDR-02/03 exigen ignorar servidores externos (Gmail añade la suya) y
degradar a `desconocido`, nunca a `pass`. El parser propio evita dependencias y es
100 % testeable con la tabla de decisión.

**Alternativas descartadas**: librería `authheaders` (dependencia poco mantenida, no
fijada en el repo); regex simple sobre la cadena (frágil ante comentarios y múltiples
métodos); confiar en la última cabecera sin comparar authserv-id (viola AC-HDR-02).

## D5 — Dominio organizacional y similitud

**Decisión**: `tldextract.TLDExtract(suffix_list_urls=())` (PSL **empaquetado**, cero
descargas: garantiza Art. II.5) para obtener el dominio organizacional (sld + tld).
Distancia de edición **Damerau-Levenshtein restringida (OSA)** implementada en el
paquete (~20 líneas, funciones puras): dos dominios se parecen si la distancia entre
sus formas normalizadas es ≤ `UMBRAL_DISTANCIA_EDICION = 2` (valor del M03). La
comparación jamás es por subcadena: `empresa.com.co` (organizacional
`empresa.com.co`) y `empresa.com` quedan a distancia 3 → no se activa nada (AC-HDR-04).

**Razón**: el hint de la spec y el M03 piden `tldextract` y Damerau-Levenshtein ≤ 2.
La PSL empaquetada hace deterministas las pruebas. OSA es suficiente para typosquatting
(transposiciones de dos letras) y evita una dependencia nativa.

**Alternativas descartadas**: `python-Levenshtein`/`textdistance` (dependencia
nativa/C para una función de 20 líneas, Art. III.8/YAGNI); comparar con `endswith`
sobre sufijos (justo el fallo por subcadena que prohíbe FR-003); descargar la PSL en
pruebas (no determinista, Art. II.5).

## D6 — Homoglifos y punycode

**Decisión**: constante `MAPA_HOMoglifos` (~30 pares: cirílico/griego → latino, por
ej. `а→a`, `ο→o`, `і→i`, más dígitos homóglifos) usada para normalizar ambos lados
antes de comparar; un dominio `xn--` se decodifica con `punycode` de la stdlib y se
compara también. `DOMINIO_PARECIDO` se activa si la forma normalizada empata o queda a
distancia ≤ 2 de un dominio propio o marca protegida; `DOMINIO_PUNYCODE` se activa de
forma independiente si el dominio contiene un label `xn--` (catálogo 5.1: 10 pts).

**Razón**: los edge cases de la spec exigen punycode/homoglifos; la tabla es un
constante nombrada (Art. III.6), no una lista mágica dispersa.

**Alternativas descartadas**: librería `confusable-homoglyphs` (dependencia pesada
para un mapeo acotado); ignorar homoglifos (deja el flanco abierto que la spec cierra).

## D7 — Adapter RDAP: cliente, caché, timeout y fallos

**Decisión**: `ClienteRDAP` (Protocol) con implementación real `RequestsRDAP`:
`GET https://rdap.org/domain/{dominio}` (URL exacta del M04b), timeout de
`TIMEOUT_RDAP_SEGUNDOS = 5`, parseo del evento `eventAction="registration"` →
`eventDate` (ISO 8601). Caché **en memoria** por proceso: solo éxitos, con TTL de
`DIAS_CACHE_RDAP = 7` (FR-006); los fallos se memoizan dentro de la misma invocación
(sin TTL inventado). Cualquier fallo (timeout, 4xx/5xx, JSON inválido, sin evento de
registro, fecha ilegible, dominio con forma inválida) → `DOMINIO_EDAD_DESCONOCIDA`
(informativa, 0 pts, sin excepción: AC-HDR-06, SC-003). Registro < 30 días →
`DOMINIO_NUEVO` (alta, 15 pts). El dominio se sanea con regex estricta de labels
(`[a-z0-9-]`, sin esquema, sin `/`) antes de componer la URL: host fijo `rdap.org`
sobre HTTPS (Art. V.5, anti-SSRF/inyección de path). Las respuestas RDAP son DATO
nunca instrucción (Art. 0.2): solo se extrae `eventDate`, no se interpretan otros
campos.

**Razón**: FR-006/AC-HDR-06 y M04b fijan URL, caché, timeout y comportamiento de
fallo. La inyección del protocolo por parámetro cumple II.5 (dobles en pruebas) y
III.7 (la red vive en un solo módulo).

**Alternativas descartadas**: caché en disco/Redis (no hay requisito de persistencia,
YAGNI); cachear los fallos con TTL de 7 días (inventaría un valor y enlentecería la
recuperación); sin caché (cada correo repetiría la consulta, lentitud innecesaria);
levantar excepción ante caída (viola AC-HDR-06).

## D8 — Tope de 60 puntos

**Decisión**: el motor suma los puntos de todas las banderas activas y publica
`puntos_totales = min(suma, TOPE_PUNTOS_BANDERAS)` con `TOPE_PUNTOS_BANDERAS = 60`
(catálogo 5.1: "tope total de banderas = 60"; AC-HDR-05). La **lista** de banderas
conserva todas las activas con su detalle: el tope recorta la suma reportada, no la
evidencia. La suma máxima teórica del catálogo es 160 puntos, por lo que el tope
afecta combinaciones reales. Valores límite: 61 → 60; 60 → 60.

**Razón**: AC-HDR-05 define exactamente ese comportamiento y sus dos pruebas de
valor límite.

**Alternativas descartadas**: descartar banderas hasta caber en 60 (pierde
evidencia/explicabilidad, contra el objetivo de la spec); tope por familia (no lo pide
nadie).

## D9 — Configuración (env, sin pydantic-settings)

**Decisión**: `ConfigBanderas` (Pydantic) construido por `desde_entorno()` leyendo
`AUTHSERV_ID`, `DOMINIOS_PROPIOS`, `MARCAS_PROTEGIDAS`, `CONTACTOS_INTERNOS`,
`TERMINOS_INTERNOS`, `DOMINIOS_GRATUITOS`, `PROVEEDORES_ENVIO` (listas separadas por
coma, minúsculas, sin espacios). Defaults documentados:
`DOMINIOS_GRATUITOS = gmail.com, hotmail.com, outlook.com, yahoo.com, live.com,
icloud.com, proton.me, protonmail.com` (decisión de diseño, como `MB = 1024²` en la
002 D6: no es una regla de dominio, es una lista **sustituible** por env); el resto
vacío por defecto. Con `AUTHSERV_ID` vacío, ninguna cabecera es de confianza →
todo `desconocido` + `AUTH_NO_EVALUABLE` (conservador, V.1). Formato inválido →
`ConfiguracionError` al construir (fail-fast, Art. III.9). Las pruebas unitarias
construyen `ConfigBanderas` directamente, sin tocar el env (II.5).

**Razón**: Art. III.6 exige constantes o configuración para listas y umbrales; la
spec marca como "configurables" los dominios propios, marcas y authserv-id (VI.2
prohíbe inventarlos). El patrón env+dotenv ya es el del repo (no hay módulo de
configuración central: cada entrada carga su `.env`).

**Alternativas descartadas**: `pydantic-settings` (dependencia nueva para 7 vars,
YAGNI y rompe el patrón del repo); valores hardcodeados de marcas/dominios (inventaría
valores de dominio, Art. VI.2); un archivo de config en disco (formato nuevo sin
necesidad).

## D10 — Técnicas de prueba (Art. II.2)

**Decisión**: 5 técnicas, con las dos obligatorias aplicables incluidas:

1. **Análisis de valores límite** (obligatoria, hay umbrales numéricos): tope 60/61
   (AC-HDR-05), distancia 1/2/3, fechas 23 h/25 h futuras y 364/366 días de antigüedad,
   registro 29/30/31 días, timeout 5 s y caché 6d23h/7d.
2. **Tablas de decisión** (obligatoria, reglas con varias condiciones): parser RFC 8601
   (authserv-id coincide/no × método presente/ausente × resultado pass/fail/softfail/
   neutral/none/permerror/temperror).
3. **Partición de equivalencia**: familias de banderas y orígenes de correo (con/sin
   cabeceras, From interno/externo).
4. **Integración con dobles**: `ClienteRDAP` falso (nunca red real en CI, II.5).
5. **Regresión**: `tests/test_pipeline.py` debe seguir verde.

Complemento: propiedades con `hypothesis` (ya fijado) sobre la distancia de edición
(simétrica, cero si y solo si iguales, ≥ |len a − len b|).

**Razón**: mínimo constitucional de 3 técnicas, superado; cada AC queda cubierta por
la técnica adecuada.

**Alternativas descartadas**: solo cobertura sin técnicas (viola II.2); pruebas contra
RDAP real (viola II.5).

## D11 — Alcance: sin wiring al pipeline

**Decisión**: el paquete expone `evaluar_banderas(...)` y nada más: **sin** cambios en
`agent.py`, `prompts.py`, el poller ni `EmailData`. El resultado lo consumen las specs
007 (scoring) y 008 (motor de decisión); la spec 12 lo devolverá en la API con la
forma ya anticipada en `PLAN_MODIFICACIONES` 14.x.

**Razón**: Art. VI.1 (solo lo que pide la spec: "producir banderas"); los AC son
unitarios sobre la producción de banderas, no sobre el veredicto. A diferencia de la
002 (que sí tocó el poller porque **reemplazaba** una ruta legacy), aquí el cambio es
aditivo y sus consumidores son specs futuras.

**Alternativas descartadas**: cablear `analyze_email` para que acumule banderas (mezcla
alcances: el agente aún no las usa y el veredicto es de la 008; tocarlo ahora rompería
"una spec = una rama = un alcance").

## D12 — Severidades, detalle y PII

**Decisión**: severidades como literales en minúscula `baja|media|alta|informativa`
(mapeo directo de "Baja/Media/Alta/Informativa" del catálogo, en la forma que ya usa
el contrato de la API en `PLAN_MODIFICACIONES` 14.x). El campo `detalle` describe
**dominios y evidencias** ("dominio From paypa1.com a distancia 1 de marca paypal.com"),
nunca contiene direcciones de correo completas (Art. V.4: se evita propagar PII hacia
reportes y API; el enmascarado de la entrada ya lo hizo la 002).

**Razón**: el contrato JSON de la API (línea 540 del plan) usa `"severidad": "alta"` y
`{"codigo","severidad","puntos","detalle"}`; V.4 es un MUST.

**Alternativas descartadas**: severidades Capitalizadas (rompen el contrato 14.x);
detalles con la cabecera completa cruda (arrastraría PII y ruido).

## D13 — Determinismo del reloj (FECHA_ANOMALA)

**Decisión**: `evaluar_banderas` acepta `ahora: datetime | None` (default:
`datetime.now(timezone.utc)`). `FECHA_ANOMALA` compara el `Date` contra `ahora`
inyectada: > 24 h en el futuro o > 1 año en el pasado (catálogo 5.1). Las pruebas
inyectan `ahora` fijo; el parser de `Date` usa `email.utils.parsedate_to_timezone` y
normaliza a UTC (fechas sin zona → UTC, decisión documentada: RFC 5322 permite zona
ausente).

**Razón**: Art. II.5 prohíbe "hora sin controlar"; inyectar `ahora` además mejora la
reproducibilidad del motor completo (mismo correo + config + ahora → mismo resultado).

**Alternativas descartadas**: `freezegun` (dependencia nueva para un parámetro);
usar el reloj real en pruebas (no determinista, viola II.5).

## D14 — Señales de "interno" (NOMBRE_SUPLANTA y REMITENTE_EXTERNO_COMO_INTERNO)

**Decisión**: reglas puras sobre listas configurables (D9), sin IA:
`NOMBRE_SUPLANTA` = el nombre visible del `From` contiene (normalizado: minúsculas, sin
tildes, coincidencia por palabra) una marca protegida o un contacto interno, con
dominio del correo externo. `REMITENTE_EXTERNO_COMO_INTERNO` = el remitente es externo
y el asunto o el texto contienen un término interno configurado (p. ej. "mesa de ayuda
interna"), misma normalización. Con listas vacías, ambas banderas quedan inactivas
(inercia segura: no penalizan sin configuración).

**Razón**: las reglas del catálogo 5.1 hablan de "marca", "nombre de un contacto
interno" y "contenido que aparenta ser interno": sin listas configurables esas
señales no existen, y VI.2 prohíbe inventar valores; con listas vacías por defecto no
se penaliza a nadie por configurar de más.

**Alternativas descartadas**: detección por modelo de lenguaje (la spec exige "sin
usar IA"); listas hardcodeadas de directivos (inventaría datos de la empresa).

## D15 — `RECEIVED_INCONSISTENTE` heurística acotada

**Decisión**: dos comprobaciones puras sobre las cabeceras `Received` (en orden físico,
la primera es el salto más reciente): (a) sus marcas de tiempo son
**no crecientes** hacia abajo (cada salto anterior es igual o más antiguo); (b) la
primera cabecera no nace en una IP privada/reservada (`ipaddress` de stdlib con las
mismas redes del M04b: 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, ::1, fc00::/7,
fe80::/10). Si no hay cabeceras `Received`, la bandera no se activa (un correo de la
API no las trae).

**Razón**: la regla del catálogo es "saltos fuera de orden o IP privada en el primer
salto externo"; validar toda la cadena de `from`/`by` sería un proyecto aparte (YAGNI).
La stdlib cubre IPs sin dependencias.

**Alternativas descartadas**: parser completo de la gramática `Received` (enorme,
frágil entreMTAs); ignorar la bandera (viola FR-005/AC-HDR-01).

## Técnicas y verificación (resumen)

- Trazabilidad: `@pytest.mark.ac("AC-HDR-01..06")` + `scripts/check_trazabilidad_ac.py`.
- Cobertura: `verify.py` mide `src/level2_agent/banderas/` con `--cov-branch`.
- Compuertas: ruff, `mypy --strict`, `check_longitud_archivos.py`, `check_nombre_rama.py`
  (`feature/banderas-cabeceras` cumple la regex del Art. I.2).

## [VERIFICAR] (Art. VI.3)

1. `authserv-id` real de la pasarela de correo propia → se configura en `AUTHSERV_ID`
   en `.env` (no está en ningún documento del repo).
2. Comportamiento real del servicio RDAP (formato de `events`/`eventDate`) → quickstart
   con paso manual de red, fuera de CI.
3. Cabeceras reales que Gmail entrega al poller (orden y forma de su
   `Authentication-Results`) → quickstart con correo real cuando haya `token.json`.
