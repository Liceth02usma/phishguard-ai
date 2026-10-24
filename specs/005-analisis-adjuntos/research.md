# Research: Análisis Estático de Adjuntos

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Fecha**: 2026-10-22

Resolución de las preguntas abiertas del *Technical Context* y de los puntos que la
spec deja como "configurable" o como hint de diseño. Cada decisión usa el formato
**Decisión / Razón / Alternativas descartadas**. Los valores de dominio (límites,
códigos, severidades, puntos) NO se inventan: salen de FR-001..FR-007, del catálogo
5.3 o del módulo M05 de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` (Art. VI.2); lo que
es lista configurable se marca como tal.

## D1 — Ubicación del código

**Decisión**: paquete nuevo `src/level2_agent/adjuntos/` (10 módulos), importado como
`src.level2_agent.adjuntos`, cuya entrada son los bytes en memoria del adjunto
(`payload: bytes`) más su `nombre` y `tipo_declarado` — los mismos campos que ya trae
`Adjunto` de la spec 002.

**Razón**: espejo de `normalizacion/` (spec 002) y de `banderas/` (spec 003): misma
capa, mismas convenciones. La spec 005 analiza **cada adjunto por separado**, y sus
consumidores (006 por hash, 008 por reglas duras) necesitan el resultado por adjunto,
no un `EmailData` completo.

**Alternativas descartadas**: dentro de `normalizacion/` (allí se **extraen** los
adjuntos; aquí se **juzgan**: rol distinto y dependencia circular de catálogos);
`src/adjuntos/` de nivel superior (rompe la cohesión con `models.py` y los
consumidores level2).

## D2 — Patrón de diseño

**Decisión**: **Strategy** (un detector puro por familia de riesgo, con interfaz común
`Protocol` `Detector` → `evaluar(ctx) -> list[BanderaAdjunto]`) + **Registry**
(lista ordenada de detectores en `motor.py`) + **Adapter** (`AnalizadorOffice` como
`Protocol`; implementación real `OlevbaOffice` con `oletools`; en pruebas, un doble).

**Razón**: Art. III.5 los nombra como candidatos previstos (Strategy para reglas,
Adapter para dependencias externas). AC-ADJ-03/04 exigen banderas específicas por
caso: la estrategia 1:1 con la familia hace que cada prueba mapee a una unidad
pequeña y trazable. El Adapter cumple III.7 ("las dependencias externas se acceden
por interfaces para poder simularlas"): `olevba` es la única dependencia "opaca" del
paquete y vive tras su protocolo.

**Alternativas descartadas**: una función gigante con if/else por tipo de archivo
(estalla el límite de 500 líneas del Art. III.1 y rompe la trazabilidad AC→código);
motor de reglas externo o antivirus YARA (dependencia pesada, YAGNI: la spec pide
detección estática acotada).

## D3 — Tipo real por firma: `filetype` (no `python-magic`)

**Decisión**: `filetype==1.2.0` (MIT, **puro Python, cero dependencias**) para detect
el tipo real por *magic bytes* desde `io.BytesIO(payload)`. El M05 autoriza
explícitamente "`python-magic` o `filetype`".

**Razón**: `python-magic` requiere la biblioteca nativa `libmagic` (DLL en Windows):
la plataforma primaria del repo es Windows (AGENTS.md/README usan `.venv\Scripts\`),
y agregar una binaria nativa a CI y a las máquinas de desarrollo es fricción real a
cambio de nada (los formatos que nos interesan — PDF, ZIP, OLE2, OOXML, ejecutables
PE, imágenes — tienen firmas simples que `filetype` cubre). Es pure-Python y fijable.

**Alternativas descartadas**: `python-magic`/`python-magic-bin` (dependencia nativa
no oficial en Windows); tabla de firmas hecha a mano (reinventar `filetype`,
más código que mantener, Art. VI.1); libmagic vía `file` del sistema (abriría un
proceso por adjunto: contra FR-006 "sin aplicaciones del sistema" y no determinista).

## D4 — Extensiones: riesgo, doble extensión, HTML/SVG (FR-003)

**Decisión**: reglas puras sobre el **nombre** del adjunto, con listas configurables
(D9). La extensión que manda es la **última**; se comparan en minúsculas:

| Condición (sobre la extensión final y el nombre) | Bandera |
|---|---|
| ext final ∈ `extensiones_riesgo` | `ADJ_EXTENSION_RIESGO` |
| ext final ∈ `extensiones_html` (html, htm, svg) | `ADJ_HTML` |
| ext final ∈ riesgo ∪ html **y** existe una ext anterior ∈ `extensiones_documental` ∪ riesgo (`factura.pdf.exe`) | `ADJ_DOBLE_EXTENSION` (además de la bandera anterior) |
| espacios en blanco justo antes de la extensión final (`factura .pdf`, regex `\s+\.[^.]+$`) | `ADJ_DOBLE_EXTENSION` |

Defaults tomados **textualmente del M05**: riesgo = `exe, scr, com, msi, dll, js,
vbs, ps1, bat, cmd, hta, wsf, lnk, iso, img, vhd`; html = `html, htm, svg` (htm es la
misma familia HTML del M05). `extensiones_documental` (para detectar la ext "cebo" de
la doble extensión) es una lista de **diseño documentado** — no viene en el M05 —
con default `pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp, txt, csv, jpg,
jpeg, png, gif`: son los formatos que un atacante usa como apariencia; es
**sustituible** por env como cualquier otra lista (Art. VI.2: no es una regla
inventada, es configuración con default razonable y declarado).

**Razón**: AC-ADJ-03 exige `factura.pdf.exe` → `ADJ_DOBLE_EXTENSION`; el M05 añade
"espacios antes de la extensión" a la misma bandera. HTML/SVG reciben `ADJ_HTML` y
**no** `ADJ_EXTENSION_RIESGO` (el catálogo 5.3 las separa: 10 pts vs 20 pts).

**Alternativas descartadas**: contar puntos por extensión sin lista (no detecta
doble extensión); usar `os.path.splitext` simple (con `factura.pdf.exe` devuelve solo
`.exe` y pierde la ext intermedia; además `os.path` invoca semántica de ruta sobre
nombres hostiles — D14).

## D5 — `ADJ_TIPO_NO_COINCIDE`: solo con firma concluyente (FR-002)

**Decisión**: la comparación se activa **solo cuando `filetype` devuelve un tipo
concluyente**; se mapea el tipo detectado a una familia esperada de la extensión
(pdf, zip, office-ole, office-ooxml, imagen, ejecutable, html) y se compara también
con el `Content-Type` declarado (si no está vacío). Cualquier discrepancia activa
`ADJ_TIPO_NO_COINCIDE` con un `detalle` que dice **cuál** ("extensión .pdf, firma
exe"; "extensión .docx, content-type application/pdf"). Archivos de texto plano
/scripts no tienen firma: `filetype` devuelve `None` → **sin bandera** (no hay
evidencia de discrepancia; `ADJ_EXTENSION_RIESGO` ya cubre ese flanco).

**Razón**: AC-ADJ-03 exige que un `.exe` renombrado a `.pdf` active la bandera (la
firma PE "MZ" es concluyente). Afirmar discrepancia sin firma sería inventar
evidencia (Art. VI.2) y castigaría legítimamente a `.txt`, `.csv` o scripts, que
nunca llevan *magic bytes*.

**Alternativas descartadas**: activar la bandera ante cualquier `filetype=None`
(inundaría de falsos positivos a todo archivo de texto); comparar solo el
`Content-Type` declarado (es mintible por definición: lo pone el atacante).

## D6 — Office: olevba tras Adapter + relaciones OOXML (FR-004)

**Decisión**: dos caminos, ambos en `office.py`:
1. **OOXML** (docx/xlsx/pptx: son un zip): con `zipfile` sobre `BytesIO`, se busca
   `word/vbaProject.bin` (o `xl/`, `ppt/`) → `ADJ_MACRO`; se escanean los `*.rels`
   buscando `TargetMode="External"` → `ADJ_ENLACE_EXTERNO`. Sin dependencias extra.
2. **OLE2** (doc/xls/ppt): `AnalizadorOffice` (Protocol) con implementación real
   `OlevbaOffice` que llama a `oletools.olevba.VBA_Parser` sobre `BytesIO(payload)`;
   hallazgo de macro → `ADJ_MACRO`; indicadores de referencia externa de olevba →
   `ADJ_ENLACE_EXTERNO`. Cualquier excepción de olevba se degrada a `detalle` +
   `ADJ_ARCHIVO_SOSPECHOSO` (V.1), nunca propaga.

**Razón**: el hint de la spec nombrа `oletools`; olevba es el estándar de facto para
macros estáticas. Las relaciones OOXML son XML plano: escanearlas con regex stdlib
es determinista, sin red y más robusto que pedirle a una librería que " liste
vínculos". El Adapter permite probar el motor sin parsear OLE2 reales (Art. III.7).

**Alternativas descartadas**: solo olevba para todo (depende de que olevba detecte
"external links" con nombres de indicador que cambian entre versiones — [VERIFICAR]);
librería `olefile` directa (habría que reimplementar la detección de VBA: YAGNI);
abrir el documento con Office/LibreOffice (viol FR-006: "sin aplicaciones del
sistema").

## D7 — PDF: `pypdf` de solo lectura + escaneo crudo (FR-004)

**Decisión**: `pypdf==6.21.2` (pure Python) sobre `io.BytesIO(payload)` en modo solo
lectura: se recorre el catálogo (`/Root` → `/OpenAction`, `/Names` → `/JavaScript`,
acciones por página `/AA`) buscando las tres acciones peligrosas; **además**, escaneo
de bytes crudos del archivo por los literales `/JavaScript`, `/OpenAction` y
`/Launch` (defensa en profundism: cubre PDFs que pypdf no llegue a abrir).
Cualquier hallazgo → `ADJ_PDF_ACTIVO`. Si el PDF **no es parseable** (truncado,
inválido) y no hubo hallazgos crudos → `ADJ_ARCHIVO_SOSPECHOSO` (fallar hacia
revisar, V.1); un PDF vacío con extensión `.pdf` sigue esta misma regla.

**Razón**: FR-004 pide exactamente `/JavaScript`, `/OpenAction` y `/Launch`. El
escaneo crudo solo **suma** evidencia (nunca la resta) y es inmune a que pypdf
cambie su tolerancia entre versiones. El mapeo "no parseable → sospechoso" sale del
Art. V.1: un verificador incompleto no puede producir "sin indicadores".

**Alternativas descartadas**: solo escaneo crudo (los *object streams* comprimidos
esconden los literales: un PDF hostil real los usa); `PyPDF2` (deprecado, sin
mantenimiento); parsear con `pdfminer` (más pesado y su objetivo es texto, no
acciones); ejecutar el PDF (FR-006 lo prohíbe).

## D8 — Zip: `zipfile` stdlib con streaming y tope duro (FR-005)

**Decisión**: `zipfile.ZipFile(io.BytesIO(payload))` con **límites nombrados**
(Art. III.6): `ADJ_LIMITE_ENTRADAS_ZIP = 100`, `ADJ_LIMITE_DESCOMPRIMIDO_ZIP =
100 MiB` (misma interpretación MB = MiB que `LIMITE_BYTES_CORREO` de la spec 002),
`ADJ_RATIO_MAXIMO_ZIP = 100`. La inspección **nunca extrae a disco** y lee por
**streaming con tope duro**: cada miembro se lee en bloques y se aborta en cuanto el
acumulado supera el tope o la relación real descomprimido/comprimido > 100 — sin
confiar en los tamaños declarados (`ZipInfo` puede mentir: es un archivo hostil).
Semántica de borde (convención de la spec 002: en el valor justo **no** hay
bandera): 100 entradas OK / 101 → `ADJ_ARCHIVO_SOSPECHOSO`; ≤ 100 MiB OK / más →
bandera; relación 99:1 y 100:1 OK / 101:1 → bandera + aborto (AC-ADJ-04). Cifrado
por el bit 0x1 de `ZipInfo.flag_bits` → `ADJ_CIFRADO` (no se intenta leer el
contenido: se sube el riesgo, M05). Un nombre tipo `.zip` (por extensión o firma)
cuyo `ZipFile` falle (zip truncado/corrupto) → `ADJ_ARCHIVO_SOSPECHOSO`; si nada
indica zip, el detector se salta (sin ruido para el 99 % de adjuntos). Relación con
división por cero: `compress_size == 0` con `file_size > 0` → relación infinita →
bandera; ambos 0 (archivo vacío) → sin riesgo. Zips anidados: **un solo nivel**
(la spec no pide recursión).

**Razón**: FR-005/AC-ADJ-04 fijan 100/100 MB/100:1 textualmente; el streaming con
tope es lo que cumple SC-002 ("abortar **sin agotar la memoria**"): comprobar solo
`ZipInfo.file_size` declarado no protege de una zip bomb que miente.

**Alternativas descartadas**: `zipfile` extrayendo todo en memoria y midiendo
después (una bomba de 10 GB agota la RAM antes de la medición — literalmente lo que
SC-002 prohíbe); `libarchive`/`patool` (dependencias nativas, D3); extraer a un
temporal medido (escribiría a disco: FR-006 lo prohíbe).

## D9 — EICAR: helper en memoria, jamás en el repo (AC-ADJ-02, SC-003)

**Decisión**: `tests/unit/vector_eicar.py` (módulo **helper**, no prueba) con
`generar_eicar() -> bytes` que devuelve la cadena estándar EICAR (68 bytes,
inofensiva) construida en memoria, y la constante `EICAR_SHA256` con el hash
publicado de la cadena. La prueba AC-ADJ-02 verifica que
`analizar_adjunto("eicar.com", ..., generar_eicar()).sha256 == EICAR_SHA256`; el
helper queda **importable por la spec 006** para su prueba integrada de VirusTotal
con respuesta grabada (el EICAR "queda disponible", como pide el AC).

**Razón**: SC-003 prohíbe guardar archivos maliciosos en el repositorio; el EICAR
es una **cadena** (no binaria), pero aun así se genera en memoria por coherencia y
para que ningún escáner de antivirus del repo lo marque. El hash de referencia debe
ser una constante **publicada**, no calculada en el momento (si lo calculáramos con
`hashlib` en la misma prueba, la prueba sería circular).

**Alternativas descartadas**: un fixture `tests/fixtures/eicar.com` en disco (viola
SC-003 y dispara antivirus); calcular el hash esperado en la prueba (circular: no
verificaría nada); omitirlo (viola AC-ADJ-02).

## D10 — Configuración (env, sin pydantic-settings)

**Decisión**: `ConfigAdjuntos` (Pydantic) construido por `desde_entorno()` leyendo
`ADJ_EXTENSIONES_RIESGO`, `ADJ_EXTENSIONES_HTML`, `ADJ_EXTENSIONES_DOCUMENTO`
(listas separadas por coma, minúsculas), `ADJ_LIMITE_ENTRADAS_ZIP` (default 100),
`ADJ_LIMITE_DESCOMPRIMIDO_ZIP` (default 104857600 = 100 MiB) y
`ADJ_RATIO_MAXIMO_ZIP` (default 100). Formato inválido (entero no numérico, límite
≤ 0) → `ConfiguracionError` al construir (fail-fast, Art. III.9). Las pruebas
unitarias construyen `ConfigAdjuntos` directamente, sin tocar el env (II.5); los
defaults viven como constantes nombradas en `configuracion.py`.

**Razón**: Art. III.6 exponde constantes o configuración; FR-003 dice "lista
**configurable** de extensiones de riesgo" y VI.2 prohíbe inventar valores: los
defaults del M05 documentados aquí son la fuente. El patrón env+dotenv ya es el del
repo (cada entrada carga su `.env`; no hay módulo central de configuración) y es el
mismo que la spec 003 diseñó para `ConfigBanderas`.

**Alternativas descartadas**: `pydantic-settings` (dependencia nueva para 6 vars,
YAGNI y rompe el patrón del repo); listas hardcodeadas sin env (FR-003 pide
"configurable"); un archivo de config en disco (formato nuevo sin necesidad).

## D11 — Técnicas de prueba (Art. II.2)

**Decisión**: 6 técnicas, con las dos obligatorias aplicables incluidas:

1. **Análisis de valores límite** (obligatoria, hay umbrales numéricos): relaciones
   99:1 / 100:1 / 101:1 (AC-ADJ-04), entradas 100 / 101, descomprimido
   100 MiB−1 / 100 MiB / 100 MiB+1, payload de 0 bytes.
2. **Tablas de decisión** (obligatoria, reglas con varias condiciones): tabla
   extensión × firma × `Content-Type` × disposición → banderas (D4/D5), y zip:
   cifrado × entradas × tamaño × relación → banderas.
3. **Partición de equivalencia**: familias de archivo (ejecutable, script, Office
   OOXML, Office OLE2, PDF, zip, imagen, texto plano) con un representante cada una.
4. **Pruebas basadas en propiedades** (`hypothesis`, ya fijado): con bytes y
   nombres **arbitrarios**, `analizar_adjunto` nunca lanza excepción no controlada,
   produce hashes en formato válido y es determinista (misma entrada → misma salida)
   (AC-ADJ-06).
5. **Seguridad**: nombres hostiles (`..`, rutas absolutas `C:\...`, `/etc/passwd`,
   nombres con RTL/NUL), verificación **estática AST** de que el paquete no contiene
   escritura a disco ni ejecución (AC-ADJ-05), y EICAR/zip bomb solo en memoria.
6. **Regresión**: `tests/test_pipeline.py` debe seguir verde.

**Razón**: mínimo constitucional de 3 técnicas, superado; cada AC queda cubierta por
la técnica adecuada (AC-ADJ-01 → referencia externa; AC-ADJ-04 → valores límite;
AC-ADJ-05 → seguridad/AST; AC-ADJ-06 → propiedades).

**Alternativas descartadas**: solo cobertura sin técnicas (viola II.2); pruebas con
archivos reales de malware descargados de internet (SC-003, Art. 0.5 y II.5).

## D12 — Verificación de "nunca escribe a disco ni ejecuta" (AC-ADJ-05)

**Decisión**: doble verificación. (a) **Prueba estática AST**: un test recorre
`src/level2_agent/adjuntos/*.py` con `ast` y **prohíbe** cualquier llamada a
`open(...)`, los módulos `subprocess`, `os.startfile`, `webbrowser`, `shutil`, y los
métodos `Path.write_*`/`Path.unlink` — el paquete no abre ni un archivo de lectura:
todo llega como `bytes` y `zipfile`/`pypdf` trabajan sobre `BytesIO`. (b) **Prueba
funcional**: se ejecuta el análisis completo de todos los fixtures dentro de un
`tmp_path` y se afirma que el directorio queda **vacío** al terminar.

**Razón**: AC-ADJ-05 es "ningún camino de código escribe adjuntos en disco con su
nombre original ni los ejecuta": una prueba funcional sola no cubre **todos** los
caminos; el gate AST sí es exhaustivo sobre el paquete, y la prueba funcional captura
efectos no previstos (p. ej. una dependencia que escriba un temporal).

**Alternativas descartadas**: solo inspección manual (el AC es "Auto"); prohibir solo
`open` en modo escritura (aún así el nombre original llegaría al sistema de
archivos: el paquete no debe abrir **nada**); mockear `open` (no cubre `subprocess`
ni métodos de `Path`).

## D13 — Detalles sin nombres de archivo completos (Art. V.4)

**Decisión**: regla de diseño: los `detalle` citan **extensiones, tipos y hechos**
("extensión .exe, firma pdf", "zip con 101 entradas"), nunca el nombre completo del
adjunto. El nombre completo solo vive en el campo `nombre` de `AnalisisAdjunto`, que
esta spec no persiste ni envía a nadie.

**Razón**: V.4 exige enmascarar PII antes de persistir o enviar a terceros; los
nombres de adjuntos pueden contener correos o datos personales ("factura_ana@empresa
..."), y los `detalle` son lo que termina en reportes, logs y tickets (specs 007/008/
010). Espejo del diseño D12 de la spec 003 (detalles sin direcciones de correo).

**Alternativas descartadas**: detalle con el nombre completo (arrastra PII hacia los
reportes de forma evitable); enmascarar el nombre con regex (innecesario: basta con
no citarlo).

## D14 — Degradación: los detectores nunca propagan excepciones

**Decisión**: cada detector envuelve su lógica y, ante cualquier entrada hostil
(zip corrupto, OLE2 inválido, nombre con NUL, payload gigante), devuelve banderas +
`detalles` en vez de excepción; `analizar_adjunto` es la única API pública y **nunca
lanza** por datos (solo `ConfiguracionError` al construir la config, que es error de
programador, no de datos). Las banderas de degradación siguen V.1: archivo que debía
inspeccionarse y no pudo → `ADJ_ARCHIVO_SOSPECHOSO`, no "sin indicadores".

**Razón**: AC-ADJ-06 exige que vacío, truncado y nombres con `..` no lancen; el
Art. V.1 exige fallar hacia revisar; los adjuntos son datos no confiables por
definición (Art. 0.2: el contenido de un correo es DATO, nunca instrucción — y aquí
también nunca código que se ejecute).

**Alternativas descartadas**: excepción propia `AdjuntoInvalido` que el llamador
maneja (el llamador es el pipeline de specs futuras: forzarlas a try/except por
adjunto multiplica el riesgo de un manejo olvidado; el resultado con bandera ya
transporta la información).

## D15 — Alcance: sin wiring y sin cambios en `models.py`

**Decisión**: el paquete expone `analizar_adjunto(...)` y nada más: **sin** cambios
en `agent.py`, `prompts.py`, el poller ni `EmailData`/`Adjunto` (D12). El resultado
lo consumen las specs 006 (consulta VT por `sha256`) y 008 (reglas duras con los
puntos del catálogo 5.3); la spec 011 decidirá la persistencia.

**Razón**: Art. VI.1 (solo lo que pide la spec: "producir banderas y hashes"); los
AC son unitarios sobre la producción de banderas, no sobre el veredicto. Los
payloads viven solo durante la normalización (spec 002): cablear ahora
`normalizacion` para que llame al analizador mezclaría alcances y obligaría a
modificar el contrato `EmailData` que las specs 003/004 comparten; el patrón ya
funcionó así en la spec 003 (D11 allá).

**Alternativas descartadas**: añadir `banderas` a `Adjunto` en `models.py` (rompe el
contrato de la spec 002 y su contrato de API sin que nadie lo consuma aún);
cablear `analyze_email` (mezcla alcances: el agente aún no usa estas banderas y el
veredicto es de la 008).

## Técnicas y verificación (resumen)

- Trazabilidad: `@pytest.mark.ac("AC-ADJ-01..06")` + `scripts/check_trazabilidad_ac.py`.
- Cobertura: `verify.py` mide `src/level2_agent/adjuntos/` con `--cov-branch`.
- Compuertas: ruff, `mypy --strict`, `check_longitud_archivos.py`,
  `check_nombre_rama.py` (`feature/analisis-adjuntos` cumple la regex del Art. I.2),
  `pip-audit` y `gitleaks` sobre las dependencias nuevas.

## [VERIFICAR] (Art. VI.3)

1. API exacta de `oletools.olevba.VBA_Parser` con objetos file-like en memoria (acepta
   `io.BytesIO`; si no, se le pasa un `SpooledTemporaryFile` **en memoria** — jamás un
   archivo con el nombre original: FR-006) y nombres de los indicadores de "enlace
   externo" en la versión fijada 0.60.2.
2. Excepciones concretas que `pypdf` lanza con PDFs malformados (para mapear todas a
   `ADJ_ARCHIVO_SOSPECHOSO` sin dejar pasar ninguna por la red del `except`).
3. Cobertura real de `filetype==1.2.0` con formatos ambiguos que use la plantilla
   corporativa (webarchive, eml renombrado): si un formato frecuente queda sin
   detectar, se documenta como `tipo desconocido` (sin bandera, D5) y no como fallo.
