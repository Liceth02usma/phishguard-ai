# Research: Normalización y Saneado de Correo (spec 002)

Investigación y decisiones técnicas para eliminar los `NEEDS CLARIFICATION` del plan.
Formato: Decisión / Rationale / Alternativas consideradas.

## D1 — Arquitectura: paquete `src/level2_agent/normalizacion/` con etapas puras

**Decisión**: paquete nuevo con un módulo por etapa del pipeline de normalización:

| Módulo | Responsabilidad |
|---|---|
| `parseo_mime.py` | bytes MIME / `.eml` / payload API → `CorreoBruto` (cabeceras, partes, adjuntos crudos) |
| `html_a_texto.py` | HTML → texto visible limpio (función pura) |
| `extraccion.py` | URLs (href/src/action/texto) y adjuntos (nombre, tipo, tamaño, SHA-256) |
| `limites.py` | 5 constantes de umbral + evaluación → banderas |
| `enmascarado.py` | PII → vistas seguras (funciones puras) |
| `__init__.py` | API pública: `normalizar_desde_gmail/eml/api`, `enmascarar_para_terceros` |

**Rationale**: patrón **Pipeline** (etapas encadenadas de funciones puras, Art. III.5) con
**Adapter** en la entrada (tres orígenes → mismo `CorreoBruto`). Funciones puras: pruebas
directas sin dobles, determinismo (II.5) y cobertura alta factible (II.3). Además respeta
III.1 (cada módulo < 200 líneas estimado) y III.7 (una responsabilidad por módulo).

**Alternativas descartadas**: (a) un solo `normalizacion.py` — superaría 500 líneas o
acumularía responsabilidades; (b) vivir en `gmail_integration/` — la API (`.eml`/JSON) no
tiene relación con Gmail; (c) modificar `email_to_emaildata.py` existente — solo puebla el
modelo desde un dict de Gmail, sin parseo ni saneado, y su contrato lo usan el poller y las
pruebas de regresión.

## D2 — Parseo MIME: stdlib `email` con `policy=default`

**Decisión**: `email.message_from_bytes(raw, policy=policy.default)` para Gmail crudo y
`.eml`; payloads API se convierten a `CorreoBruto` por el mismo camino cuando traen `raw`
en Base64, o directamente desde campos. Los niveles de anidación MIME se miden recorriendo
`walk()` con un contador de profundidad (máximo `LIMITE_NIVELES_MIME`).

**Rationale**: lo manda el plan maestro (M02: "Librería estándar `email` con
`policy=email.policy.default`") y la spec (hint). `policy.default` da cabeceras como
`Header` con decodificación correcta y preserva el orden y las repetidas (AC-NORM-01).

**Alternativas descartadas**: `distlib`/`mailparser` (dependencias externas innecesarias);
`email.parser.BytesParser` con `policy.compat32` (no decodifica bien charset/adjuntos).

## D3 — Cabeceras: lista ordenada de pares, repetidas conservadas

**Decisión**: `Cabecera(nombre: str, valor: str)` y `email_data.cabeceras: List[Cabecera]`
con `raw_items` del mensaje (`msg.raw_items()` preserva orden y duplicados exactos). El
campo legacy `headers: str` sigue existiendo (ver D4) y se rellena desde la lista.

**Rationale**: `raw_items()` es la única API estándar que devuelve las cabeceras en orden
físico con las repetidas (AC-NORM-01: dos `Received` → dos `Cabecera`, en orden).
`msg.items()` colapsa duplicados (mal para `Received`).

**Alternativas descartadas**: `msg.items()` (pierde repetidas); diccionario (prohibido
explícitamente por el plan M02); conservar el `str(dict)` actual (solo 5 cabeceras, sin orden).

## D4 — Compatibilidad de `EmailData`: ampliar sin romper (decisión crítica)

**Decisión**: `EmailData` se AMPLÍA con campos nuevos con valores por defecto
(`cabeceras`, `texto_limpio`, `urls`, `adjuntos`, `origen`, `banderas`, `revision_manual`)
y se conservan intactos los seis campos legacy (`htmlBody`, `headers`, `subject`,
`recipient`, `textBody`, `message_id`). El normalizador puebla AMBOS juegos de campos de
forma coherente. `htmlBody` gana `Field(exclude=True)` (FR-001: "solo en memoria, nunca
persistido"). Los consumidores actuales (`genetic_logic._parsear_headers`, `prompts.py`,
`agent.py`) NO se tocan en lo que respecta a campos legacy; migran a `cabeceras`/`urls`/
`adjuntos` en las specs 003 (banderas de cabeceras), 004 (URLs) y 005 (adjuntos), según el
mapa de specs (`docs/specs.md`).

**Rationale**: la spec pide un modelo "ampliado" (FR-001), no un reemplazo. Cambiar el tipo
de `headers` de `str` a lista rompería `_parsear_headers` (que espera str/dict), el prompt
del agente y las fixtures de `test_pipeline.py` — fuera de alcance (VI.1) y violaría IV.1a
(la suite existente debe seguir verde). Con defaults, cualquier `EmailData(...)` existente
sigue construyéndose sin cambios (regresión, técnica 6).

**Riesgo aceptado**: coexistencia temporal de dos representaciones de cabeceras. Mitigación:
el normalizador deriva `headers` de `cabeceras` (fuente única de verdad) y la spec 003
elimina el legacy al migrar su consumidor. Anotado en el informe final.

## D5 — HTML a texto: `HTMLParser` de la estándar, sin dependencias nuevas

**Decisión**: subclase de `html.parser.HTMLParser` que (1) ignora por completo
`<script>`, `<style>`, comentarios (`handle_comment` vacío) y CDATA de script, (2) marca
texto como oculto cuando el elemento tiene `style` con `display:none`, `visibility:hidden`,
`font-size:0` o `color` igual al `background-color`, (3) conserva el texto de los anchors
(`<a>texto</a>` → `texto`). Salida: texto plano con bloques separados por doble salto.

**Rationale**: reglas de "texto oculto" muy específicas (spec FR-003): BeautifulSoup exige
igual trabajo manual sobre estilos inline y añade dependencia; `lxml` añade binario C
(problemático en Windows). `HTMLParser` es estándar, puro y testeable caso por caso.

**Alternativas descartadas**: BeautifulSoup4 + soupsieve (dependencia nueva sin ventaja para
estilos inline); `html2text` (conserva texto oculto y estructura no pedida); regex (prohibido
por robustez: HTML malformado es la norma en phishing).

## D6 — "25 MB" = 25 × 1024 × 1024 bytes (decisión de diseño, no regla de dominio)

**Decisión**: `LIMITE_BYTES_CORREO = 25 * 1024 * 1024` (MiB). El chequeo aplica a
`len(raw_bytes)` de la entrada ANTES de parsear.

**Rationale**: la spec dice "correo ≤ 25 MB" sin definir MB. En Python la convención binaria
es la habitual y es determinista; se documenta como decisión de diseño (no invención de
regla: el umbral 25 lo da la spec). Gmail usa decimal (25 000 000) como límite de adjunto;
la diferencia (1.2 MB) no cambia ningún caso de prueba salvo el construido a propósito.

**Alternativas descartadas**: 25 000 000 bytes (convención decimal, igualmente válida — se
elige la binaria por convención de Python y se fija aquí para que las pruebas sean exactas).

## D7 — Límites: evaluar, marcar, acotar

**Decisión**: tabla de conducta por límite (todas las acciones son constantes, sin magia):

| Límite | Constante | Si excede | Si está en el límite exacto |
|---|---|---|---|
| Bytes de entrada | `LIMITE_BYTES_CORREO` (26 214 400) | bandera + `revision_manual` (objeto se construye con lo parseable) | sin bandera |
| Caracteres de texto | `LIMITE_CARACTERES_TEXTO` (20 000) | bandera + truncar `texto_limpio` a 20 000 | sin bandera, sin truncar |
| URLs | `LIMITE_URLS` (200) | bandera + conservar las primeras 200 | sin bandera |
| Adjuntos | `LIMITE_ADJUNTOS` (20) | bandera + conservar los primeros 20 (con su hash) | sin bandera |
| Niveles MIME | `LIMITE_NIVELES_MIME` (10) | bandera + ignorar partes a profundidad > 10 | sin bandera |

Toda excedencia agrega `BANDERA_LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"` (nombre exigido por
la spec) y pone `revision_manual = True` (Art. V.1: fallar hacia revisar).

**Rationale**: los cinco umbrales y la bandera salen textualmente de FR-004. Acotar
(truncar/conservar prefijo) es lo que hace al objeto "acotado" (objetivo del M02); el
correo sigue siendo analizable con la parte válida + bandera.

**Alternativas descartadas**: descartar el correo completo al exceder (pérdida de señal
analizable, contraría "acotado"); no acotar solo bandera (el LLM recibiría 20k+ caracteres,
violando 0.6 y el límite).

## D8 — Enmascarado: funciones puras + vista `enmascarar_para_terceros()`

**Decisión**: `enmascarar_texto(texto: str) -> str` aplica, en este orden:
1. Correos: `([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})` →
   `\1***@\2` (primera letra + `***` + dominio; AC-NORM-05: `juan.perez@empresa.com` →
   `j***@empresa.com`).
2. Números: `\d[\d\s-]{11,18}\d` (13–19 dígitos con espacios o guiones opcionales) →
   `[NÚMERO_OCULTO]`.

`enmascarar_para_terceros(email_data) -> EmailData` devuelve una copia con `subject`,
`recipient`, `textBody`, `htmlBody` (truncado a `LIMITE_CARACTERES_TEXTO`), `headers` y los
valores de `cabeceras` enmascarados, EXCEPTO el valor de la cabecera `From` (remitente,
exento por FR-005). El campo `origen`, `message_id` (hash-like de Gmail) y `adjuntos` no
contienen PII por diseño (solo hash/nombre/tipo/tamaño… el nombre de archivo puede contener
correos: se enmascara el nombre en la vista).

**Rationale**: FR-005 + Art. V.4. La vista separada (no mutar el objeto original) permite
que el genético (nivel 3) trabaje con la evidencia completa mientras el LLM y la futura
persistencia (spec 11) reciben solo la vista enmascarada. `agent.py` la aplica al armar el
prompt (2 líneas) — así AC-NORM-04 es verificable de extremo a extremo.

**Aplicación en el agente**: el prompt actual recibe `{htmlBody}` y `{headers}`
(`prompts.py`); con D4 y esta decisión, `agent.py` pasa esos valores desde la vista
enmascarada. `prompts.py` no cambia. El truncado a 20k del html para el modelo cumple a la
vez FR-004 y Art. 0.6.

**Alternativas descartadas**: enmascarar en el modelo mismo (rompería el genético y la
evidencia forense); enmascarar solo al persistir (dejaría PII hacia Gemini, tercerо по FR-005).

## D9 — Bandera `ENTRADA_DEGRADADA` para AC-NORM-06

**Decisión**: constante `BANDERA_ENTRADA_DEGRADADA = "ENTRADA_DEGRADADA"`. Se agrega cuando
(1) el parseo no produce cuerpo ni cabeceras, (2) una parte individual falla al decodificar
(se decodifica con `errors="replace"` y se registra), o (3) la entrada es vacía o
inparseable (no se lanza excepción no controlada: se captura de forma explícita, se
construye un `EmailData` mínimo con la bandera y `revision_manual=True`).

**Rationale**: AC-NORM-06 exige "no lanza excepción no controlada y se marca para revisión
manual". "Se marca" necesita un marcador observable: la bandera es el mecanismo existente
de la spec (banderas + `revision_manual`). El nombre no viene de la spec; es necesidad de
diseño documentada aquí (VI.2: no inventar REGLAS de dominio — este es un nombre de
constante interno, anotado en data-model.md).

**Alternativas descartadas**: silenciar sin bandera (imposible de probar/auditar); lanzar
excepción controlada y capturarla en el poller (viola "no lanza excepción" y deja al resto
de specs sin forma de detectarlo).

## D10 — Extensión de compuertas de calidad al código nuevo (necesaria, sin bajar umbrales)

**Decisión**: el código nuevo vive en `src/`, hoy excluido de las compuertas de spec 000.
Se amplía `scripts/verify.py` para que:
- `lint`: `ruff check scripts/ tests/unit/ src/level2_agent/models.py src/level2_agent/normalizacion/`
  (ruff, sin `force-exclude`, revisa rutas pasadas explícitamente aunque `src` esté en
  `extend-exclude`);
- `tipos`: `mypy` sobre las mismas rutas, con override en `pyproject.toml`:
  `module = ["src.level2_agent.models", "src.level2_agent.normalizacion*"]`,
  `ignore_errors = false, strict = true` (los overrides posteriores ganan sobre el
  `src.* ignore_errors` de spec 001);
- `cobertura`: `--cov=scripts --cov=src/level2_agent/normalizacion --cov=src/level2_agent/models`
  (combinado; `scripts/` ya está en 82 %, el paquete nuevo se prueba completo).

**Rationale**: Art. III.4/IV.1d exigen ruff+mypy sobre el código nuevo; II.3 exige medir su
cobertura. Ampliar el alcance de las compuertas es análogo al cambio de CI de spec 001
(D8 de aquella): extiende la red de calidad, no baja ningún umbral (el `fail_under` queda
igual y la media combinada no puede bajar si el código nuevo está bien probado).

**Alternativas descartadas**: dejar `src/` fuera (violación constitucional); tipar todo
`src/` legado ahora (scope creep enorme, D4/specs 003–15 lo refactorizan).

## D11 — Integración del poller: bytes crudos al normalizador

**Decisión**: `gmail_reader` expone `get_message_raw(service, msg_id) -> bytes` (mismo
`format="raw"` + base64 de hoy); `gmail_poller.process_message` llama
`normalizar_desde_gmail(raw_bytes, message_id)` en lugar de
`get_message_details` + `gmail_to_emaildata`. `email_to_emaildata.py` queda intacto
(legacy; sus usuarios se migran en specs posteriores). La prueba de integración usa un
servicio Gmail falso que devuelve bytes de un `.eml` de fixture.

**Rationale**: SC-001 exige que "cualquier entrada … produce un EmailData con la misma
forma": el único punto de entrada real hoy es el poller. Mínimo cambio (8 líneas),
verificable con dobles (Art. II.5), sin tocar OAuth ni etiquetas.

**Alternativas descartadas**: envolver en `get_message_details` (ya parsea con `compat32`
de facto y pierde orden/repetidas — el parseo debe ser UNO solo, en el normalizador).

## D12 — `hypothesis` como dependencia de prueba fijada

**Decisión**: agregar `hypothesis` a `requirements.txt` con versión fija exacta (la que
resuelva `pip install hypothesis` en la fase de tareas; se congela en ese commit). Se usa
solo en `test_ac_norm_04_enmascarado.py` (propiedades: la salida nunca contiene correos ni
cadenas de ≥13 dígitos; enmascarar es idempotente; 12 dígitos no se tocan; el dominio se
conserva; el remitente se conserva).

**Rationale**: la spec lo señala explícitamente ("pruebas con `hypothesis` para el
enmascarado") y el Art. II.2 lo lista como técnica de propiedades. CI ya instala
`requirements.txt` (paso agregado en spec 001).

**Alternativas descartadas**: generar cadenas a mano (cobertura de casos pobre para una
regla regex de PII); no fijar versión (III.8 pide versiones fijas).

## Técnicas de prueba (Art. II.2 — resumen para tasks.md)

| # | Técnica | Requisito / AC | Dónde |
|---|---|---|---|
| 1 | Análisis de valores límite (**obligatoria**) | Los 5 umbrales (en el límite vs +1); dígitos 12/13/19/20; local-part de 1 letra | `test_ac_norm_03`, `test_ac_norm_04/05` |
| 2 | Tablas de decisión (**obligatoria**) | 5 límites × {dentro, en límite, excedido}; 3 condiciones degradadas → `revision_manual`; remitente vs resto en enmascarado | `test_ac_norm_03`, `test_ac_norm_06`, `test_ac_norm_05` |
| 3 | Partición de equivalencia | Orígenes {gmail, api, .eml}; multipart vs simple; con/sin adjuntos | todos los AC |
| 4 | Propiedades con `hypothesis` | Ninguna cadena generada sobrevive sin enmascarar; idempotencia | `test_ac_norm_04` |
| 5 | Integración con dobles | Poller con servicio Gmail falso → `EmailData` normalizado | `test_integracion_poller` |
| 6 | Regresión | `tests/test_pipeline.py` y suite unitaria existente siguen verdes (D4) | suite completa |
