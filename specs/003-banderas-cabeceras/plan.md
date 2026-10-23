# Implementation Plan: Banderas Deterministas de Cabeceras y Remitente

**Branch**: `feature/banderas-cabeceras` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-banderas-cabeceras/spec.md`

## Summary

Construir un paquete determinista `src/level2_agent/banderas/` que, partiendo de un
`EmailData` normalizado (spec 002), produzca el conjunto de banderas de cabeceras y
remitente del catálogo 5.1 — 16 códigos con severidad, puntos y detalle, sin IA —:
SPF/DKIM/DMARC leídos de un `Authentication-Results` (RFC 8601) **solo del
`authserv-id` configurado**, identidad del remitente (Reply-To, Return-Path, Message-ID,
nombre visible que suplanta), comparación de dominios por **dominio organizacional**
(`tldextract` con lista de sufijos públicos empaquetada, sin red) con distancia de
edición ≤ 2, homoglifos y punycode, señales de contexto (Received, fecha, Reply-To
gratuito) y antigüedad del dominio vía un **Adapter RDAP** con caché de 7 días y
timeout de 5 s cuyas caídas se registran como `DOMINIO_EDAD_DESCONOCIDA` sin penalizar
ni excepcionar. La suma de puntos de todas las banderas del correo queda **techo a 60**.
Patrones: Strategy (una clase por bandera), Registry (lista de evaluadores) y Adapter
(RDAP). Nueva dependencia de producción: `tldextract` con versión fijada. TDD con rojo
confirmado, 5 técnicas de prueba (valores límite y tabla de decisión, ambas
obligatorias, más partición, dobles y regresión) y trazabilidad AC-HDR-01..06. Sin
cambios en `agent.py` ni en el poller: el wiring a las specs que consumen banderas
(007/008) queda fuera de alcance (research D11).

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10)

**Primary Dependencies**: pydantic y `requests` (ya presentes en `requirements.txt`);
NUEVA dependencia de producción: `tldextract` (PSL empaquetado, `suffix_list_urls=()`,
versión fijada); tooling: pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks;
`hypothesis` (ya fijada) para propiedades de la distancia de edición

**Storage**: N/A — la persistencia de análisis llega en spec 11 (M14); la caché de RDAP
es un diccionario en memoria con TTL de 7 días por proceso (sin caché en disco)

**Testing**: pytest con `@pytest.mark.ac("AC-HDR-NN")`, tabla de decisión y valores
límite sobre el parser RFC 8601 y los umbrales, dobles (`ClienteRDAP` falso, cero red),
`--cov --cov-branch` sobre `scripts/` y el paquete nuevo; ruff y `mypy --strict` sobre
el código nuevo

**Target Platform**: Windows local + Linux CI (GitHub Actions `verify.yml`)

**Project Type**: librería dentro de `src/` (paquete `banderas`) consumida por las specs
007 (scoring) y 008 (motor de decisión); sin endpoint ni binario propio

**Performance Goals**: evaluación en memoria por correo, sin E/S salvo RDAP; cada
consulta RDAP con timeout de 5 s y caché de 7 días; cero red en pruebas (Art. II.5)

**Constraints**: determinismo (mismo correo + config + `ahora` → mismo resultado; la
hora se inyecta, no se lee el reloj en pruebas); ningún `.py` > 500 líneas (objetivo
300); funciones ≤ 40 líneas y ≤ 5 parámetros; `mypy --strict` (Art. III.4)

**Scale/Scope**: ~9 módulos nuevos en `src/level2_agent/banderas/`, ~9 archivos de
prueba en `tests/unit/`, 1 dependencia de producción nueva fijada, extensión de las
compuertas de `verify.py`/`pyproject.toml` al paquete nuevo y creación de
`.env.example` con la configuración M03. Nada fuera de
`specs/003-banderas-cabeceras/` y de esos archivos; **sin** cambios en `agent.py`,
`prompts.py` ni en el poller (research D11)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS | `feature/banderas-cabeceras` creada desde `main` (1459ebe) antes de cualquier código de la spec; cumple regex Art. I.2 |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | Commits `feat|test|docs: ... (AC-HDR-NN)` en la rama; la única escritura previa en `main` (5fbcd36) es desviación autorizada del usuario, de bookkeeping de la spec 012, y no pertenece a esta spec |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase TDD dedicada en tasks.md; rojo verificado contra un paquete inexistente |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 5 técnicas en `research.md` D10: valores límite (obligatorio: tope 60/61, distancia 1/2/3, fechas 24 h/1 año, 29/30/después de 30 días, 5 s, 7 días), tabla de decisión (obligatorio: authserv-id × método × resultado), partición de equivalencia (familias de banderas), integración con dobles (`ClienteRDAP` falso), regresión (`test_pipeline.py` verde) |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | `verify.py` y `pyproject.toml` se EXTENDEN para medir `src/level2_agent/banderas/` (ampliación de alcance, no bajada de umbral; mismo mecanismo D10 de la spec 002) |
| II.4 | Sin pruebas sin `assert` | PASS | Toda prueba verifica banderas observables, estados de autenticación, puntos o el detalle devuelto |
| II.5 | Sin red real ni hora sin controlar | PASS | `tldextract` con `suffix_list_urls=()` (PSL empaquetado); RDAP tras el protocolo `ClienteRDAP` sustituido por doble; `ahora` se inyecta como parámetro (FECHA_ANOMALA no lee el reloj en pruebas) |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-HDR-01..06")`; verificado con `scripts/check_trazabilidad_ac.py --spec specs/003-banderas-cabeceras/spec.md` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica ninguna prueba existente; `fail_under` no baja (el código nuevo se prueba completo) |
| III.1 | Archivos `.py` ≤ 500 líneas (objetivo 300) | PASS | 9 módulos por familia de banderas; estimado cada uno < 200 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | Estrategias puras de 1 regla c/u; el orquestador recibe `(correo, config, ahora, cliente_rdap)` (4 parámetros) |
| III.3 | `snake_case` en español sin tildes | PASS | `evaluar_banderas`, `dominio_organizacional`, `distancia_edicion`, `TOPE_PUNTOS_BANDERAS` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict` ampliado al paquete nuevo; `BanderaActivada`/`ResultadoBanderas`/`ConfigBanderas` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Strategy (una clase por bandera), Registry (lista de evaluadores) y Adapter (RDAP), nombrados en `research.md` D2/D3/D7; nada más |
| III.6 | Sin números ni cadenas mágicas | PASS | `TOPE_PUNTOS_BANDERAS=60`, `UMBRAL_DISTANCIA_EDICION=2`, `DIAS_CACHE_RDAP=7`, `TIMEOUT_RDAP_SEGUNDOS=5`, `DIAS_DOMINIO_NUEVO=30`, `DIAS_FECHA_FUTURA=1`, `ANIOS_FECHA_VIEJA=1`, catálogo 5.1 como dict nombrado; el resto es configuración (`ConfigBanderas` desde env) |
| III.7 | Una responsabilidad por módulo | PASS | Un módulo por familia: autenticación, identidad, dominios, contexto, RDAP; el motor solo orquesta y aplica el tope |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | `tldextract` con versión fija al agregarse; ruff/mypy sobre el paquete nuevo |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` vacíos: las caídas de RDAP se MODELAN como `DOMINIO_EDAD_DESCONOCIDA` (FR-006); error propio `ConfiguracionError` en la construcción de la config |
| IV.1a–i | Definición de terminado | PASS | verify.py exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar | PASS | `AUTH_NO_EVALUABLE` (5 pts) ante autenticación no evaluable empuja a revisión; `DOMINIO_EDAD_DESCONOCIDA` es informativa **sin penalizar** por decisión explícita de FR-006/SC-003; esta spec no emite veredictos (specs 007/008) |
| V.2 | Acciones externas por código determinista | PASS | Sin acciones externas; la única E/S es la consulta RDAP, tras Adapter |
| V.3 | Secretos fuera de reposo | PASS | Sin claves nuevas; RDAP no requiere autenticación; las pruebas no leen `.env` |
| V.4 | PII enmascarada antes de persistir/enviar a terceros | PASS | Los `detalle` describen **dominios y evidencias**, nunca direcciones de correo completas (regla de diseño en `research.md` D12); el enmascarado de la entrada ya lo hizo la spec 002 |
| V.5 | Adjuntos/URLs en memoria, sin ejecutar, con límites; SSRF | PASS | El dominio se sanea con regex estricta antes de componer la URL RDAP; host fijo `https://rdap.org` sobre HTTPS; nada se descarga ni ejecuta |
| V.8 | API con X-API-Key única, sin roles | N/A | Esta spec no expone endpoints |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-006; URLs, adjuntos, VirusTotal y veredicto quedan fuera (spec 003, Assumptions) |
| VI.2 | No inventar valores | PASS | Puntos, severidades, umbrales (60, ≤2, 5 s, 7 días, 30 días, 24 h, 1 año) salen textualmente del catálogo 5.1/M03/spec; las listas (authserv-id, dominios propios, marcas, gratuitos, contactos internos) son **configurables** vía env con defaults documentados en `research.md` D9, no reglas de dominio inventadas |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Quedan `[VERIFICAR]`: `authserv-id` real de la pasarela, comportamiento real de RDAP y cabeceras reales de Gmail (marcados en quickstart) |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en tasks.md |

**Resultado pre-fase 0**: SIN violaciones → se procede a research.
**Re-evaluación post-fase 1**: sin cambios de alcance; D8 (techo de 60 puntos),
D11 (sin wiring al pipeline) y D13 (hora inyectada) confirman los gates PASS sin
bajar umbrales ni inventar valores.

## Project Structure

### Documentation (this feature)

```text
specs/003-banderas-cabeceras/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── banderas-api.md  # Phase 1 output (API pública del paquete banderas)
├── checklists/
│   └── requirements.md  # checklist de requirements (scaffolding de specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── models.py                    # SIN CAMBIOS (EmailData ya trae cabeceras ordenadas, message_id, texto_limpio)
│   ├── agent.py                     # SIN CAMBIOS (el wiring lo hacen las specs 007/008 — D11)
│   ├── normalizacion/               # SIN CAMBIOS (sigue exponiendo EmailData)
│   └── banderas/                    # NUEVO paquete (FR-001..FR-006)
│       ├── __init__.py              #   API pública: evaluar_banderas, ConfigBanderas, ResultadoBanderas
│       ├── modelos.py               #   BanderaActivada, ResultadoBanderas, catálogo 5.1 (código→severidad/puntos)
│       ├── configuracion.py         #   ConfigBanderas desde env + ConfiguracionError (authserv-id, listas)
│       ├── autenticacion.py         #   RFC 8601: AR del authserv-id propio → SPF/DKIM/DMARC + AUTH_NO_EVALUABLE (FR-001, FR-002)
│       ├── identidad.py             #   REPLY_TO_DISTINTO, RETURN_PATH_DISTINTO, NOMBRE_SUPLANTA, MESSAGE_ID_DISTINTO, REMITENTE_EXTERNO_COMO_INTERNO (FR-005)
│       ├── dominios.py              #   tldextract + Damerau-Levenshtein + homoglifos/punycode (FR-003, FR-004)
│       ├── contexto.py              #   RECEIVED_INCONSISTENTE, FECHA_ANOMALA, REPLY_TO_GRATUITO (FR-005)
│       ├── rdap.py                  #   Adapter RDAP: caché 7 días, timeout 5 s → DOMINIO_NUEVO / DOMINIO_EDAD_DESCONOCIDA (FR-006)
│       └── motor.py                 #   Registry de estrategias + suma con tope de 60 (AC-HDR-05)

tests/
├── unit/
│   ├── conftest.py                  # EDITAR: fixtures para construir EmailData con cabeceras variadas
│   ├── test_ac_hdr_01_pares_bandera.py     # NUEVO (AC-HDR-01: par positivo/negativo por bandera + correo canónico)
│   ├── test_ac_hdr_02_auth_externa.py      # NUEVO (AC-HDR-02: AR externo ignorado)
│   ├── test_ac_hdr_03_auth_no_evaluable.py # NUEVO (AC-HDR-03: desconocido + AUTH_NO_EVALUABLE)
│   ├── test_ac_hdr_04_dominio_parecido.py  # NUEVO (AC-HDR-04: paypa1.com vs empresa.com.co)
│   ├── test_ac_hdr_05_tope_puntos.py       # NUEVO (AC-HDR-05: valores límite 61→60 y 60→60)
│   ├── test_ac_hdr_06_rdap_falla.py        # NUEVO (AC-HDR-06: caídas sin excepción y sin puntos)
│   ├── test_autenticacion.py               # NUEVO (parser RFC 8601: tabla de decisión)
│   ├── test_dominios.py                    # NUEVO (distancia, homoglifos, dominio organizacional, hypothesis)
│   └── test_rdap.py                        # NUEVO (caché, timeout y doble de red)
├── test_pipeline.py                 # SIN CAMBIOS (regresión: debe seguir verde)
└── fixtures/                        # SIN CAMBIOS

scripts/
└── verify.py                        # EDITAR: lint/mypy/cobertura incluyen el paquete banderas
                                     # (extensión de compuertas sin bajar umbrales)

pyproject.toml               # EDITAR: mypy override estricto para banderas.*
requirements.txt             # EDITAR: tldextract con versión fija (dependencia de producción)
.env.example                 # CREAR: AUTHSERV_ID, DOMINIOS_PROPIOS, MARCAS_PROTEGIDAS,
                             # CONTACTOS_INTERNOS, TERMINOS_INTERNOS, DOMINIOS_GRATUITOS,
                             # PROVEEDORES_ENVIO (placeholders, sin secretos)
README.md                    # EDITAR: módulo M03 y comando de pruebas
AGENTS.md                    # EDITAR: nota del paquete banderas/ y de tldextract
```

**Structure Decision**: se conserva la estructura existente; las banderas viven en un
paquete nuevo dentro de `level2_agent/` porque consumen `EmailData` de `models.py` y
las specs 007/008 lo consumirán desde ahí. Cada familia de reglas es un módulo de
estrategias puras (Strategy + Registry + Adapter, `research.md` D2/D3/D7). El paquete
**no** se conecta al pipeline en esta spec (D11): el alcance es producir banderas
verificables de forma independiente, y el wiring lo hacen las specs que las consumen.
Las compuertas de la spec 000 se EXTENDEN al paquete nuevo (mismo mecanismo de la 002):
sin eso el código nuevo quedaría sin medir y violaría II.3/III.4.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS).
