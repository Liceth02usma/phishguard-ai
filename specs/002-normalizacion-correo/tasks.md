---
description: "Task list for spec 002-normalizacion-correo"
---

# Tasks: NormalizaciÃ³n y Saneado de Correo

**Input**: Design documents from `/specs/002-normalizacion-correo/`

**Prerequisites**: plan.md, spec.md, research.md (D1â€“D12), data-model.md, contracts/normalizacion-api.md, quickstart.md

**Tests**: SÃ â€” exigidos por la constituciÃ³n (Art. II.1: TDD con rojo confirmado; II.6: trazabilidad ACâ†’prueba). Las fases de pruebas se ejecutan ANTES de la implementaciÃ³n de cada etapa.

**Organization**: Una sola user story (US1, P1) que entrega el pipeline completo de normalizaciÃ³n; los AC-NORM-01..06 se prueban dentro de ella. La spec no tiene US2/US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/`, `tests/`, `scripts/` at repository root (paquete importable como `src.level2_agent...` vÃ­a `sys.path` del root, sin `src/__init__.py`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencia nueva, extensiÃ³n de compuertas de calidad al cÃ³digo que va a nacer en `src/` (research D10) y fixtures compartidos.

- [x] T001 Instalar `hypothesis` y fijar su versiÃ³n exacta en requirements.txt (secciÃ³n "# Pruebas"; research D12)
- [x] T002 [P] Ampliar pyproject.toml: override mypy `strict=true, ignore_errors=false` para `src.level2_agent.models` y `src.level2_agent.normalizacion*` (despuÃ©s del override `src.* ignore_errors=true` existente, para que prevalezca; research D10)
- [x] T003 [P] Ampliar scripts/verify.py: lint `ruff check scripts/ tests/unit/ src/level2_agent/models.py src/level2_agent/normalizacion/`; tipos `mypy` sobre las mismas rutas; cobertura `--cov=scripts --cov=src/level2_agent/normalizacion --cov=src/level2_agent/models` (compuertas `_compuerta_lint`, `_compuerta_tipos`, `_compuerta_cobertura`; research D10 â€” sin bajar umbrales)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelo y constantes de los que depende TODO el pipeline de normalizaciÃ³n y todas las pruebas.

**?? CRITICAL**: No puede empezar US1 hasta completar esta fase.

- [x] T004 Crear `Cabecera` y `Adjunto` en src/level2_agent/models.py (campos y validaciones segÃºn data-model.md: `sha256` = 64 hex, `tamano_bytes >= 0`, nombre vacÃ­o â†’ `"adjunto_sin_nombre"`)
- [x] T005 Ampliar `EmailData` en src/level2_agent/models.py: campos nuevos con default (`cabeceras: List[Cabecera]=[]`, `texto_limpio: str=""`, `urls: List[str]=[]`, `adjuntos: List[Adjunto]=[]`, `origen: Literal["gmail","api"]="gmail"`, `banderas: List[str]=[]`, `revision_manual: bool=False`); `htmlBody` con `Field(..., exclude=True, repr=False)` (FR-001; research D4 â€” los 6 campos legacy quedan intactos)
- [x] T006 [P] Crear src/level2_agent/normalizacion/limites.py: constantes `LIMITE_BYTES_CORREO=25*1024*1024`, `LIMITE_CARACTERES_TEXTO=20_000`, `LIMITE_URLS=200`, `LIMITE_ADJUNTOS=20`, `LIMITE_NIVELES_MIME=10`, `BANDERA_LIMITE_EXCEDIDO="LIMITE_EXCEDIDO"`, `BANDERA_ENTRADA_DEGRADADA="ENTRADA_DEGRADADA"`, `TEXTO_OCULTO_MARCADOR="[NÃšMERO_OCULTO]"` (FR-004/FR-005, research D6/D9) y funciÃ³n pura `evaluar_limites(bytes_totales, texto, urls, adjuntos, profundidad) -> tuple[list[str], list[str]]` que devuelve (banderas, textos de detalle) con la tabla de D7 (acotar + bandera al exceder; nada en el lÃ­mite exacto)
- [x] T007 [P] Crear src/level2_agent/normalizacion/__init__.py y src/level2_agent/normalizacion/parseo_mime.py con el esqueleto (dataclass `CorreoBruto` con `cabeceras, cuerpo_html, cuerpo_texto, partes_adjunto, profundidad_max_mime, bytes_totales, problemas` segÃºn data-model.md) y docstrings de la API pÃºblica del contrato

**Checkpoint**: Foundation ready â€” US1 puede empezar.

---

## Phase 3: User Story 1 - Parseo y normalizaciÃ³n de cualquier correo a EmailData (Priority: P1) ?? MVP

**Goal**: convertir cualquier entrada (Gmail bytes, `.eml`, payload API) en un `EmailData` ampliado, acotado y saneado: cabeceras ordenadas con repetidas, texto limpio, URLs, adjuntos con SHA-256, 5 lÃ­mites duros con `LIMITE_EXCEDIDO`, enmascarado PII aplicado hacia el LLM, sin excepciones no controladas.

**Independent Test**: `pytest tests/unit/test_ac_norm_*.py` verde con AC-NORM-01..06 marcados, y `test_integracion_poller.py` verde (poller con doble de servicio Gmail); suite existente (regresiÃ³n) sin cambios.

### Tests for User Story 1 (TDD â€” escribir PRIMERO y confirmar rojo) ??

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation** (Art. II.1). El rojo esperado: `ModuleNotFoundError` en `src.level2_agent.normalizacion`, `ValidationError`/`TypeError` por campos inexistentes de `EmailData`, `AttributeError` en el poller.

- [x] T008 [P] [US1] AÃ±adir fixtures en tests/unit/conftest.py: constructores de `.eml` en bytes (multipart con 2 `Received`, HTML con script/comentario/texto oculto/anchor, adjunto pequeÃ±o, 201 URLs) y `RECORTE_EML_BASICO`; sin red (Art. II.5)
- [x] T009 [P] [US1] Prueba AC-NORM-01 en tests/unit/test_ac_norm_01_cabeceras.py (`@pytest.mark.ac("AC-NORM-01")`): `.eml` con 2 cabeceras `Received` â†’ `cabeceras` conserva ambas EN ORDEN y con sus valores; tambiÃ©n origen gmail/api/eml (particiÃ³n de equivalencia)
- [x] T010 [P] [US1] Prueba AC-NORM-02 en tests/unit/test_ac_norm_02_html_texto.py (`@pytest.mark.ac("AC-NORM-02")`): HTML con `<script>`, `<style>`, comentario, `display:none`, `font-size:0`, `color==background` y `<a>texto visible</a>` â†’ texto limpio SIN los ocultos y CON el texto del enlace
- [x] T011 [P] [US1] Prueba AC-NORM-03 en tests/unit/test_ac_norm_03_limites.py (`@pytest.mark.ac("AC-NORM-03")`): tabla de decisiÃ³n â€” por CADA lÃ­mite (bytes, texto, URLs, adjuntos, profundidad MIME) valor en el lÃ­mite exacto (sin bandera) y +1 (bandera `LIMITE_EXCEDIDO` + `revision_manual=True` + acotamiento: texto=20 000 chars, urls=200, adjuntos=20)
- [x] T012 [P] [US1] Prueba AC-NORM-04 en tests/unit/test_ac_norm_04_enmascarado.py (`@pytest.mark.ac("AC-NORM-04")`): `enmascarar_para_terceros` deja sin correos ni secuencias de 13â€“19 dÃ­gitos en subject/recipient/textBody/htmlBody/headers/cabeceras; From EXENTO; propiedades con `hypothesis` (idempotencia; 12 dÃ­gitos intactos, 13/19/20 enmascarados; dominio conservado; sin residuo de â‰¥13 dÃ­gitos); 25 MB de entrada exacto vs +1 byte (valor lÃ­mite)
- [x] T013 [P] [US1] Prueba AC-NORM-05 en tests/unit/test_ac_norm_05_formato_email.py (`@pytest.mark.ac("AC-NORM-05")`): `juan.perez@empresa.com` â†’ `j***@empresa.com`; `a@b.com` â†’ `a***@b.com` (local-part de 1 letra); dominios con `+`, `%`, subdominios
- [x] T014 [P] [US1] Prueba AC-NORM-06 en tests/unit/test_ac_norm_06_entradas_degradadas.py (`@pytest.mark.ac("AC-NORM-06")`): cuerpo vacÃ­o, sin cabeceras, bytes vacÃ­os y codificaciÃ³n invÃ¡lida (charset inexistente) â†’ NINGUNA excepciÃ³n no controlada, bandera `ENTRADA_DEGRADADA`, `revision_manual=True`
- [x] T015 [P] [US1] Prueba de integraciÃ³n del poller en tests/unit/test_integracion_poller.py: doble de servicio Gmail (devuelve bytes de fixture) â†’ `process_message` construye `EmailData` con `origen="gmail"`, campos nuevos poblados y llama al anÃ¡lisis; sin red
- [x] T016 [US1] Ejecutar la fase de pruebas y registrar el ROJO CONFIRMADO en el informe (module not found / campos inexistentes); sin `skip`/`xfail` (Art. II.7)

### Implementation for User Story 1

- [x] T017 [P] [US1] Implementar src/level2_agent/normalizacion/html_a_texto.py: subclase `HTMLParser` â€” sin `<script>`/`<style>`/comentarios; texto oculto por estilo inline (`display:none`, `visibility:hidden`, `font-size:0`, `color`==`background-color`); conserva texto de anchors; funciÃ³n pura `html_a_texto(html: str) -> str` (FR-003, research D5)
- [x] T018 [P] [US1] Implementar src/level2_agent/normalizacion/enmascarado.py: `enmascarar_texto` (regex correo `([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})` â†’ `\1***@\2`; dÃ­gitos `\d[\d\s-]{11,18}\d` â†’ `[NÃšMERO_OCULTO]`) y `enmascarar_para_terceros(email_data) -> EmailData` (copia; From exento; htmlBody truncado a `LIMITE_CARACTERES_TEXTO`; FR-005, research D8)
- [x] T019 [P] [US1] Implementar src/level2_agent/normalizacion/extraccion.py: `extraer_urls(html, texto) -> list[str]` (href/src/action + texto plano, deduplicadas, descartando vacÃ­as) y `extraer_adjuntos(partes) -> list[Adjunto]` (SHA-256 con `hashlib` en memoria, nunca a disco; Art. V.5, FR-001)
- [x] T020 [US1] Completar src/level2_agent/normalizacion/parseo_mime.py: `parsear(raw_bytes) -> CorreoBruto` con `email.message_from_bytes(..., policy=policy.default)` y `raw_items()` (orden + repetidas, AC-NORM-01); profundidad MIME por recorrido (mÃ¡x. `LIMITE_NIVELES_MIME`); decodificaciÃ³n con `errors="replace"` y registro en `problemas`; entrada vacÃ­a/inparseable NO lanza: degrada (FR-002, AC-NORM-06, research D2/D9)
- [x] T021 [US1] Completar src/level2_agent/normalizacion/__init__.py: orquestadores `normalizar_desde_gmail(raw_bytes, message_id)`, `normalizar_desde_eml(contenido)`, `normalizar_desde_api(payload)` que encadenan parseo â†’ html_a_texto â†’ extracciÃ³n â†’ `evaluar_limites` â†’ `EmailData` poblado (legacy + nuevos campos coherentes, D4); polÃ­tica de errores y garantÃ­as del contrato contracts/normalizacion-api.md; funciones â‰¤ 40 lÃ­neas
- [x] T022 [US1] Integrar en src/gmail_integration/gmail_reader.py: aÃ±adir `get_message_raw(service, msg_id) -> bytes` (format="raw" + `urlsafe_b64decode`); en src/gmail_integration/gmail_poller.py: `process_message` usa `get_message_raw` + `normalizar_desde_gmail(raw_bytes, msg_id)` en lugar de `get_message_details` + `gmail_to_emaildata` (research D11; `email_to_emaildata.py` queda intacto)
- [x] T023 [US1] Aplicar la vista enmascarada en src/level2_agent/agent.py (~2 lÃ­neas): los valores `{htmlBody}` y `{headers}` que van al prompt del LLM se toman de `enmascarar_para_terceros(email_data)` (AC-NORM-04 extremo a extremo, Art. 0.6/V.4; prompts.py NO cambia)
- [x] T024 [US1] Ejecutar tests/unit/ -q: VERDE â€” 0 fallos, 0 skips nuevos, AC-NORM-01..06 con su marca, suite de regresiÃ³n existente intacta

**Checkpoint**: US1 completa â€” cualquier entrada produce un `EmailData` acotado y saneado, verificable de forma independiente.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: compuertas de calidad, documentaciÃ³n afectada, informe y commits.

- [x] T025 [P] Ejecutar python scripts/verify.py â†’ exit 0 (longitud, rama, cobertura ahora sobre scripts/ + normalizacion/ + models, trazabilidad, secretos, lint, tipos; `dependencias` puede quedar advertencia no bloqueante â€” spec 014)
- [x] T026 Ejecutar python scripts/check_trazabilidad_ac.py --spec specs/002-normalizacion-correo/spec.md â†’ `6 AC cubiertos`
- [x] T027 [P] Actualizar README.md (secciÃ³n de arquitectura: paquete normalizaciÃ³n, comando de pruebas) y AGENTS.md (paquete `normalizacion/`, `hypothesis` en requirements, cobertura ahora incluye `src/level2_agent/normalizacion/` y `models.py`)
- [x] T028 Ejecutar validaciones V1â€“V5 y V7 del quickstart.md; V6 (poller con Gmail real) queda `[VERIFICAR]` documentado
- [x] T029 Redactar el informe final (Art. IV.3) en la respuesta de cierre: comando + resultado de pruebas, % cobertura (lÃ­neas y ramas), lista ACâ†’prueba, desviaciones (V6 pendiente, coexistencia temporal legacy D4)
- [x] T030 Commits Conventional Commits en la rama `feature/normalizacion-correo` mencionando AC-NORM-NN, en grupos lÃ³gicos: (1) test rojo, (2) modelos+constantes, (3) normalizaciÃ³n implementada, (4) integraciÃ³n poller+agente, (5) compuertas/docs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias â€” arranca de inmediato (T001 âˆ¥ T002 âˆ¥ T003)
- **Foundational (Phase 2)**: depende de Setup (T002 debe ir antes/ junto a la implementaciÃ³n; T004â€“T007 solo necesitan el repo) â€” BLOQUEA US1
- **US1 (Phase 3)**: depende de Foundational (los tests construyen `EmailData` ampliado y las constantes)
- **Polish (Phase 4)**: depende de US1 completa

### User Story Dependencies

- **US1 (P1)**: Ãºnica story; arranca tras Foundational. TDD: T008â€“T015 (pruebas, paralelas entre sÃ­ por archivo) â†’ T016 (rojo) â†’ T017â€“T023 (implementaciÃ³n; T017/T018/T019 paralelas por mÃ³dulo independiente) â†’ T024 (verde)

### Within User Story 1

- Pruebas escritas y ROJAS antes de implementar (Art. II.1)
- Modelos y constantes antes que parseo; parseo antes que orquestador; orquestador antes que integraciÃ³n; integraciÃ³n antes que verde

### Parallel Opportunities

- Setup: T001 âˆ¥ T002 âˆ¥ T003 (archivos distintos)
- Foundational: T006 âˆ¥ T007 (mÃ³dulos distintos del paquete nuevo)
- US1 pruebas: T008â€“T015 (8 archivos de prueba distintos)
- US1 implementaciÃ³n: T017 âˆ¥ T018 âˆ¥ T019 (html_a_texto, enmascarado, extraccion â€” sin dependencias entre sÃ­)
- Polish: T025 âˆ¥ T027

---

## Parallel Example: User Story 1

```text
# Lanzar juntas las pruebas de los AC (archivos distintos):
Task: "Prueba AC-NORM-01 en tests/unit/test_ac_norm_01_cabeceras.py"
Task: "Prueba AC-NORM-02 en tests/unit/test_ac_norm_02_html_texto.py"
Task: "Prueba AC-NORM-03 en tests/unit/test_ac_norm_03_limites.py"
Task: "Prueba AC-NORM-04 en tests/unit/test_ac_norm_04_enmascarado.py"

# Lanzar juntas las etapas puras (mÃ³dulos distintos):
Task: "Implementar src/level2_agent/normalizacion/html_a_texto.py"
Task: "Implementar src/level2_agent/normalizacion/enmascarado.py"
Task: "Implementar src/level2_agent/normalizacion/extraccion.py"
```

---

## Implementation Strategy

### MVP First (US1 = 100 % del alcance de la spec)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICAL)
3. Completar Phase 3: US1 con TDD estricto (rojo â†’ verde)
4. **PARAR y VALIDAR**: suite AC verde + regresiÃ³n intacta
5. Phase 4: Polish â†’ verify.py exit 0 â†’ informe â†’ commits

### Incremental Delivery

- Los 5 mÃ³dulos puros son verificables por separado al terminar T024 (un solo incremento coherente: la spec es un pipeline atÃ³mico; no hay valor intermedio entregable â€” se respeta MVP = US1 completa).

### Notes (verificaciÃ³n constitucional, Art. VII.3 â€” revisar al cierre, no son tareas)

- Art. II.1/II.7: rojo confirmado en T016 antes de T017â€“T023; ningÃºn `skip`/`xfail` nuevo; ninguna prueba existente modificada
- Art. II.2: 6 tÃ©cnicas (research D11): valores lÃ­mite (obligatoria), tablas de decisiÃ³n (obligatoria), particiÃ³n, propiedades hypothesis, integraciÃ³n con dobles, regresiÃ³n
- Art. II.3: cobertura â‰¥ 80 % lÃ­neas y ramas sobre `normalizacion/` + `models.py` (compuerta extendida en T003)
- Art. II.6: `@pytest.mark.ac("AC-NORM-01..06")` en T009â€“T014; verificado en T026
- Art. III.1/3.2: ningÃºn archivo > 500 lÃ­neas (verify.py lo comprueba); funciones â‰¤ 40 lÃ­neas
- Art. IV.1: verify.py exit 0 (T025) + informe (T029)
- Art. V.1/V.4/V.5: revisiÃ³n manual ante banderas; vista enmascarada al LLM (T023); adjuntos en memoria (T019)
- Art. VI.3: `[VERIFICAR]` â€” contrato payload API (spec 12) y poller con Gmail real (quickstart V6)








## Phase 5: Convergence

- [x] T031 Refactorizar `_ensamblar` (src/level2_agent/normalizacion/__init__.py) en helpers de <=40 lineas sin cambiar comportamiento, reejecutando las pruebas afectadas per Constitution III.2 (contradicts)
- [x] T032 Refactorizar `evaluar_limites` (src/level2_agent/normalizacion/limites.py) a <=40 lineas (extraer la construccion de bandera y detalles a helpers) sin cambiar el contrato per Constitution III.2 (contradicts)
- [x] T033 Truncar `headers` y `subject` en la vista que va al LLM (`enmascarar_para_terceros`) con constantes nombradas para que el texto total del correo para el modelo respete el limite; anyadir prueba de borde per Constitution 0.6 / FR-004 (partial)
- [x] T034 Retirar (o justificar por escrito y refactorizar) `get_message_details` en src/gmail_integration/gmail_reader.py: sin llamadores en el repo y con 55 lineas; decision preexistente heredada de la spec 000 per Constitution III.2 (contradicts)
- [x] T035 Sustituir los `except Exception: pass` de `agent.py::_parse_agent_response` (lineas 120-121 y 130-131) por manejo explicito con logging o relanzada per Constitution III.9 (contradicts)
- [x] T036 Anadir prueba AC-NORM-02 con texto oculto por `color` igual al `background` (y caso negativo con colores distintos que si se conserva) per FR-003 (partial)
- [x] T037 Anadir prueba de `normalizar_desde_api` con payload que incluya `headers: {k: v}` para cubrir `_correo_desde_payload` per contracts/normalizacion-api.md (partial)
- [x] T038 Anadir pruebas de las ramas defensivas de `html_a_texto`: HTML malformado que dispara el fallback parcial y etiquetas ignoradas anidadas per AC-NORM-06 / FR-003 (partial)
- [x] T039 Anadir prueba de `_destinatario_limpio` con `To` con nombre visible (`Nombre <addr@dominio>`) per FR-001 (partial)





