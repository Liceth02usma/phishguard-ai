# Implementation Plan: Análisis y Expansión de URLs

**Branch**: `feature/analisis-urls` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-analisis-urls/spec.md`

## Summary

Construir un paquete determinista `src/level2_agent/analisis_urls/` que, partiendo de
un `EmailData` normalizado (spec 002), **extraiga** las URLs de `href`, `src`, `action`,
texto plano y texto de enlaces (conservando los pares texto→destino que necesita la
bandera `URL_TEXTO_DISTINTO_DESTINO`), las **normalice** (host en minúsculas, sin
fragmentos ni parámetros de seguimiento) deduplicando tras normalizar **conservando la
original** para el reporte; aplique las **13 banderas** del catálogo 5.2 (Strategy +
Registry, con severidad/puntos/detalle); **sanee** los parámetros sensibles y los valores
con forma de correo antes de cualquier consulta externa (FR-007, AC-URL-06); y **expanda**
únicamente acortadores de una lista configurable con `HEAD` (fallback `GET` sin descargar
el cuerpo), máximo **5 saltos** y **5 s por URL**, validando en **cada salto** la IP
resuelta contra las redes privadas/loopback/metadata de FR-004 (puertos Adapter de DNS y
cliente HTTP; sin JavaScript ni descarga de cuerpos). La reputación de caché de
VirusTotal (FR-006) y la antigüedad del dominio (`URL_DOMINIO_NUEVO`, vía RDAP) llegan
tras **puertos con defaults degradados**, porque las specs 006 y 003 están en desarrollo
paralelo. **Cero dependencias nuevas**. Sin wiring al pipeline (precedente D11 de la
spec 003): `agent.py`, `prompts.py` y el poller quedan intactos; consumidoras = 006/007/008.
6 técnicas de prueba (valor límite y tabla de decisión, ambas obligatorias, más
partición, propiedades con `hypothesis`, dobles con servidor local y regresión),
trazabilidad AC-URL-01..07 y compuertas de `verify.py` extendidas al paquete nuevo.

## Technical Context

**Language/Version**: Python 3.11 local (proyecto: Python 3.10+; CI: 3.10)

**Primary Dependencies**: pydantic y `requests` (ambos ya en `requirements.txt`); stdlib
`urllib.parse`, `ipaddress`, `socket`, `html.parser`, `time`; **cero dependencias
nuevas**; tooling: pytest, pytest-cov, ruff, mypy, pip-audit, gitleaks; `hypothesis`
(ya fijada) para propiedades del saneador y de URLs arbitrarias

**Storage**: N/A — esta spec no persiste; la caché de VirusTotal (FR-006) y la consulta
RDAP (`URL_DOMINIO_NUEVO`) se consumen tras puertos con implementación por defecto en
memoria/vacía (specs 006 y 003 en ramas paralelas)

**Testing**: pytest con `@pytest.mark.ac("AC-URL-NN")`, tabla de decisión sobre la
máquina de estados de expansión y sobre la matriz SSRF, valores límite (4/5/6 saltos,
5 s, 200/201 caracteres, 30 días, URL de 100 000), dobles de DNS y cliente HTTP +
servidor local de loopback (lo exige AC-URL-02), cero red externa (Art. II.5),
`--cov --cov-branch` sobre `scripts/` y el paquete nuevo; ruff y `mypy --strict` sobre
el código nuevo

**Target Platform**: Windows local + Linux CI (GitHub Actions)

**Project Type**: librería dentro de `src/` (paquete `analisis_urls`) consumida por las
specs 006 (VT sobre URLs), 007 (scoring) y 008 (motor de decisión); sin endpoint ni
binario propio

**Performance Goals**: análisis en memoria sin E/S salvo acortadores (subconjunto
escaso); expansión ≤ 5 s y ≤ 5 saltos por URL; sin descarga de cuerpos de respuesta

**Constraints**: SSRF absoluto — ninguna conexión (ni en la primera petición ni tras
redirección ni vía DNS) a las redes de FR-004; determinismo — reloj inyectado, misma
entrada + configuración → mismo resultado; ningún `.py` > 500 líneas (objetivo 300);
funciones ≤ 40 líneas y ≤ 5 parámetros; `mypy --strict` (Art. III.4)

**Scale/Scope**: ~11 módulos nuevos en `src/level2_agent/analisis_urls/`, ~12 archivos
de prueba en `tests/unit/`, 13 banderas del catálogo 5.2, 0 dependencias nuevas;
ediciones **aditivas** y compartidas con las ramas paralelas 003/005/015 en
`scripts/verify.py`, `pyproject.toml`, `tests/unit/conftest.py`, `.env.example`,
`README.md` y `AGENTS.md`; **sin** cambios en `agent.py`, `prompts.py`, el poller ni
`normalizacion/` (research D11/D2/D14)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Requisito | Estado | Evidencia / decisión |
|---|---|---|---|
| I.1–I.3 | Rama creada primero, notación `{tipo}/{nombre}` | PASS (con nota) | `feature/analisis-urls` creada desde el HEAD con la spec 002 ya mergeada, durante la fase de plan y **sin tocar el árbol de trabajo**: el directorio está compartido con sesiones paralelas (003/005/015 activas), por lo que el checkout se hace en T00 antes que cualquier código (los artefactos son untracked y viajan con él); cumple la regex del Art. I.2 |
| I.4–I.5 | Sin commits en main; Conventional Commits con CA | PASS | Commits `feat\|test\|docs: … (AC-URL-NN)` solo en la rama; la escritura previa en `main` (5fbcd36, bookkeeping de la constitución/012) es decisión del usuario, igual que en la spec 003 |
| II.1 | Pruebas antes que código, rojo confirmado | PASS | Fase TDD dedicada en tasks.md; el rojo se confirma contra un paquete inexistente |
| II.2 | ≥ 3 técnicas de prueba justificadas | PASS | 6 técnicas en `research.md` D10: valores límite (obligatorio: 4/5/6 saltos, 5 s, 200/201, 30 días, umbral de subdominios, 100 000 caracteres), tabla de decisión (obligatorio: máquina de estados de expansión y matriz SSRF de FR-004), partición de equivalencia (familias de banderas), propiedades con `hypothesis` (saneador AC-URL-06 y no-excepción AC-URL-07), integración con dobles + servidor local (AC-URL-02/04), regresión (`test_pipeline.py` verde) |
| II.3 | ≥ 80 % líneas y ramas en código nuevo/modificado | PASS | `verify.py` y `pyproject.toml` se EXTENDEN para medir `src/level2_agent/analisis_urls/` (mismo mecanismo D10 de las specs 002/003: ampliar alcance, no bajar umbrales) |
| II.4 | Sin pruebas sin `assert` | PASS | Toda prueba verifica banderas observadas, estados de expansión, URLs sanitizadas, conexiones no realizadas o excepciones ausentes |
| II.5 | Sin red real ni hora sin controlar | PASS | DNS y cliente HTTP tras puertos sustituidos por dobles; servidor local de loopback (lo exige AC-URL-02, sin red externa); el reloj de los 5 s es inyectado (monotónico falso en pruebas) |
| II.6 | Trazabilidad AC→prueba | PASS | `@pytest.mark.ac("AC-URL-01..07")`; verificado con `scripts/check_trazabilidad_ac.py --spec specs/004-analisis-urls/spec.md` |
| II.7 | No borrar/relajar pruebas ni umbrales | PASS | No se modifica ninguna prueba existente; `fail_under` no baja |
| III.1 | Archivos `.py` ≤ 500 líneas (objetivo 300) | PASS | 11 módulos por responsabilidad; estimado cada uno < 220 líneas |
| III.2 | Funciones ≤ 40 líneas, ≤ 5 parámetros | PASS | `analizar_urls(email_data, config, deps)` agrupa la E/S en `DependenciasURLs` (3 parámetros, Art. III.2); evaluadores de bandera de 1 regla c/u |
| III.3 | `snake_case` en español sin tildes | PASS | `expandir_acortador`, `ip_permitida`, `sanitizar_parametros`, `TOPE_SALTOS=5` |
| III.4 | Tipado estricto, Pydantic, docstrings | PASS | `mypy --strict` ampliado al paquete nuevo; `UrlAnalizada`/`BanderaURL`/`ResultadoURLs`/`ConfigURLs` Pydantic; docstring en toda API pública |
| III.5 | Patrones nombrados, sin YAGNI | PASS | Strategy (una clase por bandera), Registry (lista de evaluadores), Adapter (DNS, cliente HTTP, caché VT, RDAP) — nombrados en `research.md` D1/D6/D7; nada más |
| III.6 | Sin números ni cadenas mágicas | PASS | `TOPE_SALTOS=5`, `TIMEOUT_URL_SEGUNDOS=5`, `UMBRAL_URL_LARGA=200`, `DIAS_DOMINIO_NUEVO=30`, `REDES_PROHIBIDAS` (los CIDR exactos de FR-004) y catálogo 5.2 como dicts nombrados; acortadores/TLD/tracking/umbral de subdominios = configuración con defaults documentados en research D8 |
| III.7 | Una responsabilidad por módulo | PASS | Un módulo por fase: extracción, normalización, banderas, saneo, SSRF, expansión; el motor solo orquesta |
| III.8 | ruff/mypy sin advertencias; deps fijadas | PASS | Cero dependencias nuevas; ruff/mypy sobre el paquete nuevo |
| III.9 | Manejo de errores explícito | PASS | Sin `except:` vacíos: caídas de red/DNS/timeout se MODELAN como estados (`error_controlado`, `bloqueada_ssrf`, `limite_*`); error propio `ConfiguracionError`; AC-URL-07 garantiza cero excepciones no controladas |
| IV.1a–i | Definición de terminado | PASS | `verify.py` exit 0 + informe final (Art. IV.3) |
| V.1 | Fallar hacia revisar | PASS | Esta spec no emite veredictos (007/008); las verificaciones incompletas de RDAP/VT quedan modeladas como estados degradados (`URL_DOMINIO_NUEVO` ausente cuando no hay RDAP; reputación desconocida ≠ limpia), nunca como "seguro" |
| V.2 | Acciones externas por código determinista, DRY_RUN por defecto | N/A | Sin acciones con efecto externo: la expansión es solo lectura de cabeceras (HEAD/GET) de URLs que el correo ya trae; nada se ejecuta ni se modifica |
| V.3 | Secretos fuera de reposo | PASS | Sin claves nuevas; la expansión no requiere autenticación; las pruebas no leen `.env` |
| V.4 | PII enmascarada antes de persistir/enviar a terceros | PASS | FR-007 sanea correos y tokens **antes** de toda consulta externa (AC-URL-06); los `detalle` de banderas citan host y nombres de parámetro, nunca valores sensibles (research D12) |
| V.5 | Adjuntos en memoria; SSRF validado en cada salto | PASS | **Núcleo de la spec**: FR-004 valida la IP resuelta contra `REDES_PROHIBIDAS` antes de conectar en cada petición (primera o redirección); sin JavaScript (FR-005) y sin descarga de cuerpos (AC-URL-04) |
| V.6 | Sin envío de archivos a terceros por defecto | PASS | La spec solo LEE URLs; no sube nada (la consulta VT de URLs es de la spec 006) |
| V.8 | API con X-API-Key única, sin roles | N/A | Esta spec no expone endpoints |
| VI.1 | Solo lo que pide la spec | PASS | Alcance = FR-001..FR-007; fuera: consulta a VirusTotal (06), QR, adjuntos, veredicto y formulario de credenciales (catálogo del plan sin codear en la spec) |
| VI.2 | No inventar valores | PASS | 5 saltos, 5 s, 200 caracteres, 30 días y los CIDR salen textualmente de FR-003/FR-004/M04b; acortadores, TLD de riesgo, tracking y umbral de subdominios son **configurables** con defaults documentados y marcados en `research.md` D8 |
| VI.3 | `[VERIFICAR]` lo no verificable | PASS | Quedan `[VERIFICAR]`: umbral de subdominios, lista por defecto de TLD de riesgo, comportamiento real de los acortadores, ventana TOCTOU del cliente HTTP (marcados en quickstart) |
| VII.3 | Verificación de cumplimiento en plan y tasks | PASS | Esta tabla + sección de verificación en tasks.md |

**Resultado pre-fase 0**: SIN violaciones (nota de rama I.1 resuelta en T00) → se
procedió a research.

**Re-evaluación post-fase 1** (tras `research.md`, `data-model.md`,
`contracts/analizar-urls.md`, `quickstart.md`): SIN violaciones nuevas.

- **I**: rama `feature/analisis-urls` existe; checkout en T00 antes que cualquier
  código (el árbol sigue compartido con sesiones paralelas 003/005/015, sin tocarlo).
- **II.2**: 6 técnicas documentadas en D10 (valor límite y tabla de decisión, ambas
  obligatorias, cubiertas por la máquina de estados D9 y la matriz SSRF D7).
- **II.3/III.8**: cero dependencias nuevas (`requests`+stdlib, D6); compuertas
  extendidas al paquete (E5 del quickstart).
- **V.1**: degradaciones modeladas como estados explícitos
  (`error_controlado`/`bloqueada_ssrf`/`reputacion_conocida`/sin bandera), nunca
  como "seguro" (D4/D5).
- **V.4/V.5**: FR-007 sanea antes de todo puerto externo (I3) y FR-004 bloquea por
  salto con 0 conexiones (I1) — ambas con prueba de servidor local.
- **VI.2/VI.3**: valores numéricos textuales de spec/plan (tabla de constantes en
  `data-model.md`); listas configurables propias marcadas `[VERIFICAR]` en D8 y
  V1–V7 del quickstart.
- **Sin hallazgos fuera de alcance detectados**: la exclusión de los códigos `VT_*`
  del catálogo 5.2 (pertenecen a la 006) queda documentada en `data-model.md`.

## Project Structure

### Documentation (this feature)

```text
specs/004-analisis-urls/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── analizar-urls.md # Phase 1 output (API pública del paquete analisis_urls)
├── checklists/
│   └── requirements.md  # checklist de requirements (scaffolding de specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── level2_agent/
│   ├── models.py                    # SIN CAMBIOS (EmailData ya trae urls, htmlBody, texto_limpio)
│   ├── agent.py                     # SIN CAMBIOS (wiring de 006/007/008 — D11)
│   ├── prompts.py                   # SIN CAMBIOS
│   ├── normalizacion/               # SIN CAMBIOS (extraer_urls de la 002 sigue poblando EmailData.urls)
│   └── analisis_urls/               # NUEVO paquete (FR-001..FR-007)
│       ├── __init__.py              #   API pública: analizar_urls, ConfigURLs, DependenciasURLs, ResultadoURLs, dependencias_por_defecto
│       ├── modelos.py               #   UrlAnalizada, BanderaURL, ResultadoExpansion, ResultadoURLs, catálogo 5.2 (13 códigos)
│       ├── configuracion.py         #   ConfigURLs desde env (acortadores, TLD, tracking, umbral subdominios) + ConfiguracionError
│       ├── puertos.py               #   Protocol: ResolvedorDNS, ClienteHTTPExpansion, CacheReputacionURL, ClienteRDAP, Reloj
│       ├── extraccion.py            #   pares (texto, destino) de href/src/action + texto plano y de enlaces (FR-001)
│       ├── normalizacion.py         #   host minúsculas, sin fragmentos ni tracking; dedup preservando la original (FR-001)
│       ├── banderas.py              #   Strategy + Registry: 13 evaluadores puros (FR-002)
│       ├── sanitizacion.py          #   parámetros sensibles y valores con forma de correo (FR-007)
│       ├── ssrf.py                  #   REDES_PROHIBIDAS (CIDR de FR-004) + is_global; validación por salto (FR-004)
│       ├── expansion.py             #   HEAD/GET sin cuerpo, ≤5 saltos, ≤5 s, solo acortadores (FR-003, FR-005)
│       └── motor.py                 #   orquestador: extraer → normalizar → banderas → sanitizar → expandir (si la caché no la conoce)

tests/
├── unit/
│   ├── conftest.py                  # EDITAR: fixtures EmailData con HTML/URLs variadas (compartido 003/005/015)
│   ├── dobles_red.py                # NUEVO: ResolvedorDNS/ClienteHTTP falsos + servidor local de loopback (context manager)
│   ├── test_ac_url_01_texto_vs_destino.py   # NUEVO
│   ├── test_ac_url_02_ssrf_privados.py      # NUEVO (servidor local; DNS a privada; redirección a 127.0.0.1)
│   ├── test_ac_url_03_limite_saltos.py      # NUEVO (4/5/6 saltos y 5 s)
│   ├── test_ac_url_04_sin_cuerpo.py         # NUEVO (ninguna lectura de cuerpo)
│   ├── test_ac_url_05_dedup.py              # NUEVO (duplicados tras normalizar)
│   ├── test_ac_url_06_saneado.py            # NUEVO (token/email fuera de la consulta)
│   ├── test_ac_url_07_malformadas.py        # NUEVO (vacía/malformada/100 000, hypothesis)
│   ├── test_banderas_url.py                 # NUEVO (tabla 13 códigos: par positivo/negativo + puntos)
│   ├── test_expansion.py                    # NUEVO (máquina de estados, tabla de decisión)
│   ├── test_ssrf.py                         # NUEVO (matriz de rangos FR-004)
│   └── test_sanitizacion.py                 # NUEVO (propiedades con hypothesis)
├── test_pipeline.py                 # SIN CAMBIOS (regresión: debe seguir verde)
└── fixtures/                        # SIN CAMBIOS

scripts/
└── verify.py                        # EDITAR (aditivo): --cov=src/level2_agent/analisis_urls y
                                     # RUTAS_CALIDAD_SRC incluye el paquete (compartido 003/005/015)

pyproject.toml               # EDITAR (aditivo): mypy override estricto para analisis_urls.*
.env.example                 # EDITAR (aditivo): ACORTADORES, TLD_RIESGO, PARAMETROS_TRACKING,
                             # URL_SUBDOMINIOS_MAX (sin secretos; compartido con 003/005)
requirements.txt             # SIN CAMBIOS (cero dependencias nuevas)
README.md                    # EDITAR (aditivo): módulo M04b y comando de pruebas
AGENTS.md                    # EDITAR (aditivo): nota del paquete analisis_urls/
```

**Structure Decision**: se conserva la estructura existente; el análisis de URLs vive en
un paquete nuevo dentro de `level2_agent/` porque consume `EmailData` de `models.py` y
las specs 006/007/008 lo consumirán desde ahí. Cada fase del flujo es un módulo de
funciones puras o estrategias (Strategy + Registry + Adapter, `research.md` D1/D2/D6/D7).
El paquete **no** se conecta al pipeline en esta spec (D11, precedente de la 003): el
alcance es producir resultados verificables de forma independiente. La extracción es
propia (D2) para no tocar `normalizacion/` de la 002 y para conservar los pares
texto→destino. Las compuertas de la spec 000 se EXTENDEN al paquete nuevo (mismo
mecanismo de las 002/003): sin eso el código nuevo quedaría sin medir y violaría
II.3/III.4.

## Complexity Tracking

> Sin violaciones de constitución que justificar (tabla Constitution Check: todo PASS;
> la nota del Art. I.1 es una secuencia de pasos —checkout en T00—, no una exención).
