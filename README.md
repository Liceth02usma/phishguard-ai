# PhishGuard-AI

Sistema automatizado de detección de phishing con pipeline de tres niveles: algoritmo genético, agente ReAct con IA, e integración directa con Gmail para monitoreo en tiempo real.

## Arquitectura

```
                    ┌─────────────────────────────┐
                    │       GMAIL POLLER          │
                    │  (src/gmail_integration/)   │
                    │   Cada 30s consulta buzón   │
                    └──────────┬──────────────────┘
                               │ bytes crudos (raw)
                               ▼
              ┌────────────────────────────────┐
              │   NORMALIZACIÓN (spec 002)     │
              │ src/level2_agent/normalizacion │
              │ parseo MIME · HTML→texto       │
              │ URLs · adjuntos (SHA-256)      │
              │ límites duros · enmascarado    │
              │ → EmailData acotado y saneado  │
              └──────────┬─────────────────────┘
                         │ EmailData
                         ▼
              ┌────────────────────────────────┐
              │      NIVEL 3: GENÉTICO         │
              │  src/level3_logic/genetic_logic │
              │  32 genes con pesos ajustables  │
              │  Score < 30 → BENIGNO directo   │
              │  Score > 75 → MALICIOSO directo  │
              │  30 ≤ Score ≤ 75 → pasa a Nivel 2│
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │     NIVEL 2: AGENTE ReAct      │
              │    src/level2_agent/agent.py   │
              │   Gemini 2.5 Flash Lite + RAG  │
              │   Tools:                       │
              │   ├─ RAG vectorial (NIST/OWASP)│
              │   ├─ Reputación IP (VT)        │
              │   └─ Jira (tickets de alerta)  │
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │          ACCIÓN                │
              │  ┌─ Phishing → Label "Phishing │
              │  │             Alertas" + Jira │
              │  └─ Seguro  → Marcar como leído│
              └────────────────────────────────┘
```

## Requisitos

- Python 3.10+
- MongoDB Atlas (cluster con búsqueda vectorial)
- API key de Google Generative AI (Gemini)
- Cuenta de Google Cloud con API de Gmail habilitada
- (Opcional) API key de VirusTotal
- (Opcional) Instancia de Jira

## Instalación

```powershell
# 1. Clonar el repositorio
git clone <repo-url>
cd phishguard-ai

# 2. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Configuración

### Variables de entorno (`.env`)

```bash
# Obligatorio
GOOGLE_API_KEY=tu_api_key_de_gemini
MONGODB_ATLAS_CLUSTER_URI=mongodb+srv://...

# Opcional (Jira)
JIRA_INSTANCE_URL=https://tu-instancia.atlassian.net/
JIRA_USER_EMAIL=tu-email@domain.com
JIRA_API_TOKEN=tu_token_jira

# Opcional (VirusTotal)
VT_API_KEY=tu_api_key_vt
```

### Google Cloud — Gmail API

1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com)
2. Habilitar Gmail API
3. Crear credenciales OAuth 2.0 → "Desktop application"
4. Descargar JSON como `credenciales.json` y colocarlo en la raíz del proyecto
5. La primera ejecución del poller abrirá el navegador para el consentimiento OAuth y generará `token.json`

### MongoDB Atlas

1. Crear un cluster en MongoDB Atlas
2. Habilitar Atlas Search
3. Crear base de datos `phishguard` y colección `docs_phishing`
4. Poblar la colección con documentos de referencia NIST SP 800-53 / OWASP
5. Crear índice vectorial con nombre `vector_index` sobre el campo de embeddings

## Uso

### Gmail Poller (monitoreo continuo)

```powershell
.venv\Scripts\python.exe src/gmail_integration/gmail_poller.py
```

- Revisa la bandeja de entrada cada 30 segundos
- Procesa máximo 5 correos no leídos por ciclo
- Phishing detectado → mueve a etiqueta "Phishing Alertas"
- Correos seguros → marca como leídos

### Probar el pipeline con fixtures

```powershell
.venv\Scripts\python.exe tests/test_pipeline.py
```

Evalúa 3 escenarios predefinidos:
- **benign**: Correo legítimo → score genético bajo (< 30) → ruta benigna
- **malicious**: Correo phishing → score genético alto (> 75) → ruta maliciosa
- **ai_agent**: Correo dudoso → score medio (30-75) → ruta agente ReAct

## Estructura del proyecto

```
phishguard-ai/
├── .env                         # Variables de entorno
├── credenciales.json            # Credenciales OAuth Google
├── token.json                   # Token OAuth (generado automáticamente)
├── requirements.txt
├── src/
│   ├── level2_agent/           # Pipeline de análisis principal
│   │   ├── agent.py            # Orquestador ReAct + genético
│   │   ├── models.py           # EmailData (ampliado), PhishingReport
│   │   ├── prompts.py          # System prompts NIST/OWASP
│   │   ├── normalizacion/      # Pipeline de normalización (spec 002)
│   │   │   ├── __init__.py     # Orquestadores + API pública
│   │   │   ├── parseo_mime.py  # Bytes → CorreoBruto
│   │   │   ├── html_a_texto.py # HTML → texto visible
│   │   │   ├── extraccion.py   # URLs + adjuntos (SHA-256)
│   │   │   ├── limites.py      # 5 límites duros + banderas
│   │   │   └── enmascarado.py  # PII → vista para terceros
│   │   ├── banderas/           # Banderas deterministas (spec 003, M03)
│   │   │   ├── __init__.py     # API pública: evaluar_banderas
│   │   │   ├── motor.py        # Compone 5 familias + tope 60 puntos
│   │   │   ├── modelos.py      # Catálogo 5.1 + contexto + helpers
│   │   │   ├── configuracion.py # Config por variable de entorno
│   │   │   ├── autenticacion.py # RFC 8601 + SPF/DKIM/DMARC
│   │   │   ├── dominios.py     # Distancia + homoglifos + punycode
│   │   │   ├── identidad.py    # Reply-To / Return-Path / Message-ID
│   │   │   ├── contexto.py     # Received / Date + Reply-To gratuito
│   │   │   └── rdap.py         # Edad del dominio (cache 7 días)
│   │   ├── analisis_urls/      # Análisis y expansión de URLs (spec 004, M04b)
│   │   │   ├── motor.py        # analizar_urls (API pública, sin wiring aún)
│   │   │   ├── expansion.py    # Acortadores con validación SSRF por salto
│   │   │   ├── banderas.py     # Catálogo 5.2 (13 códigos de URL)
│   │   │   ├── ssrf.py         # Redes FR-004 + is_global por hop
│   │   │   └── configuracion.py # Listas configurables vía .env
│   │   ├── adjuntos/            # Análisis estático de adjuntos (spec 005, M05)
│   │   │   ├── __init__.py     # API pública: analizar_adjunto
│   │   │   ├── modelos.py      # AnalisisAdjunto + catálogo 5.3
│   │   │   ├── configuracion.py # ConfigAdjuntos desde env
│   │   │   ├── hashes.py       # SHA-256/MD5/SHA-1
│   │   │   ├── firma.py        # Magic bytes vs extensión
│   │   │   ├── extensiones.py  # Riesgo/doble/HTML
│   │   │   ├── office.py       # Macros/enlaces (oletools)
│   │   │   ├── pdf.py          # /OpenAction /JS /Launch
│   │   │   ├── comprimidos.py  # Zip con límites
│   │   │   └── motor.py        # Registry de detectores
│   │   ├── virustotal/          # Cliente VirusTotal API v3 (spec 006, M06)
│   │   │   ├── __init__.py     # API pública: consultar_archivo/consultar_url/...
│   │   │   ├── cliente.py      # Orquestador (flujo FR-001..009, síncrono)
│   │   │   ├── clasificacion.py # Tabla M06.4 (3/3/20, umbrales configurables)
│   │   │   ├── limitador.py    # Cubeta 4/min (VT_RPM) con reloj inyectado
│   │   │   ├── resiliencia.py  # Reintentos 429/5xx + cortacircuitos 5/60 s
│   │   │   ├── cache.py        # vt_cache TTL 7d/24h/1h + vt_contador (Mongo)
│   │   │   ├── presupuesto.py  # 10 consultas por correo (FR-006)
│   │   │   ├── envios.py       # POST /files y /urls tras flags (default off)
│   │   │   ├── identificadores.py # SHA-256, URL→B64, dominio, IP
│   │   │   ├── configuracion.py # ConfigVT desde env
│   │   │   ├── puertos.py      # Protocolos + adapter httpx
│   │   │   └── modelos.py      # ResultadoVT + catálogo VT (5 códigos)
│   │   └── tools/
│   │       ├── __init__.py     # Retriever RAG vectorial
│   │       ├── ip_reputation.py # Consulta VirusTotal
│   │       └── jira_integration.py # Creación de tickets Jira
│   ├── level3_logic/           # Scoring con clasificador lineal
│   │   ├── genetic_logic.py    # 32 genes de detección (FR-004/005)
│   │   ├── modelo.py           # Carga/validación del modelo entrenado
│   │   └── scoring/            # Fachada: clasificador + banderas
│   │       ├── __init__.py
│   │       ├── motor.py        # calcular_score_final
│   │       ├── modelos.py      # ScoreFinal, BanderaScoring
│   │       └── configuracion.py
│   └── gmail_integration/      # Integración con Gmail
│       ├── gmail_auth.py       # Autenticación OAuth 2.0
│       ├── gmail_reader.py     # Lectura y acciones en Gmail
│       ├── email_to_emaildata.py # Adaptador Gmail → EmailData
│       └── gmail_poller.py     # Loop de monitoreo continuo
├── tests/
│   ├── test_pipeline.py        # Pruebas del pipeline
│   ├── unit/                   # Pruebas unitarias por AC (marcador `ac`)
│   └── fixtures/               # Datos de prueba (JSON)
├── notebooks/                   # Jupyter notebooks
├── data/                        # Datos auxiliares
├── docs/                        # Documentación adicional
└── workflow/                    # Archivos de flujo de trabajo
```

## Pipeline de detección

### Nivel 3 — Algoritmo Genético (`genetic_logic.py`)

Evalúa 32 características (genes) con pesos predefinidos:
- **Pesos positivos** (mayor riesgo): dominio externo, URL con IP, asunto de verificación, cuerpo corto
- **Pesos negativos** (mayor seguridad): apelación al miedo, fecha límite, URL acortada

El score se calcula con una función sigmoide sobre la suma lineal ponderada:
```
score = 1 / (1 + e^(-suma_genes)) × 100
```

### Nivel 2 — Agente ReAct (`agent.py`)

Para correos en zona gris (score 30-75):
1. Consulta base vectorial RAG (NIST SP 800-53 / OWASP)
2. Evalúa cabeceras (SPF, DKIM, dominios)
3. Identifica disparadores psicológicos
4. Opcional: consulta VirusTotal para IPs/URLs
5. Opcional: crea ticket en Jira si confirma phishing

### Análisis de URLs (`analisis_urls/`, spec 004)

Paquete determinista y aislado del pipeline (la integración llega en specs posteriores) que:

- **Extrae** URLs de `href`, `src`, `action`, de los pares (texto del enlace → destino) y del texto plano.
- **Normaliza y deduplica** (host en minúsculas, sin fragmento ni tracking) conservando la original.
- **Sanea** los 7 parámetros sensibles de FR-007 (`token`, `key`, `session`, `email`, `user`, `code`, `password`) y valores con forma de correo **antes** de cualquier consulta externa.
- **Expande acortadores** con validación SSRF en **cada salto** (IPs privadas/loopback/metadata bloqueadas), tope de 5 saltos o 5 s (reloj inyectado) y **sin descargar cuerpos** (`HEAD` + `stream`).
- **Bandea** con el catálogo 5.2 (13 códigos con severidad/puntos literales) vía `ResultadoURLs`.

Configuración opcional en `.env`: `ACORTADORES`, `TLD_RIESGO`, `PARAMETROS_TRACKING`, `PARAMETROS_SENSIBLES`, `URL_SUBDOMINIOS_MAX`.

```powershell
# Pruebas del módulo (85 pruebas, marcador ac + propiedades hypothesis)
python -m pytest tests/unit/ -k "ac_url or banderas_url or expansion or ssrf or sanitizacion"
```

### Acciones automáticas

| Veredicto | Acción |
|---|---|
| Benigno (score < 30) | Marcar como leído |
| Malicioso (score > 75) | Mover a etiqueta "Phishing Alertas" + ticket Jira |
| Sospechoso (30-75, IA confirma) | Mover a etiqueta "Phishing Alertas" |
| Sospechoso (30-75, IA descarta) | Marcar como leído |

### Banderas de cabeceras (spec 003, módulo M03)

Capa determinista (sin IA) que, a partir de un `EmailData` normalizado, produce las **16 banderas** del catálogo 5.1 con código, severidad, puntos y detalle:

```python
from src.level2_agent.banderas import evaluar_banderas, ConfigBanderas

config = ConfigBanderas.desde_entorno()          # AUTHSERV_ID, DOMINIOS_PROPIOS, ...
resultado = evaluar_banderas(email_data, config=config)
resultado.estados_autenticacion                  # SPF/DKIM/DMARC (RFC 8601)
resultado.banderas                               # [{codigo, severidad, puntos, detalle}]
resultado.puntos_totales                         # suma con tope de 60
```

Cinco familias de estrategias (Strategy + Registry): autenticación (`Authentication-Results` solo si `authserv-id` coincide), identidad (Reply-To/Return-Path/Message-ID y nombre visible), dominios (distancia de edición ≤2, homoglifos, punycode), contexto (`Received`/`Date` y Reply-To gratuito) y RDAP (edad del dominio con caché de 7 días). La severidad y los puntos salen **únicamente** del catálogo 5.1 (`modelos.py`), nunca se inventan en las estrategias. Configuración por variable de entorno: ver `.env.example` y `specs/003-banderas-cabeceras/`.

### Cliente VirusTotal (`virustotal/`, spec 006)

Paquete determinista y **sin wiring al pipeline** (lo consumirán las specs 007/008) que consulta la API v3 de VirusTotal sobre cuatro indicadores — archivos por SHA-256, URLs por identificador Base64 url-safe sin relleno (saneado delegando en la spec 004), dominios e IPs — y devuelve un `ResultadoVT` clasificado con la tabla M06.4 (umbrales 3/3/20 configurables):

- **Cuota pública** por defecto: cubeta de 4 solicitudes/minuto + tope diario de 500 (contador persistente en Mongo, sobrevive reinicios). El modo `premium` solo eleva los topes si se configuran `VT_RPM`/`VT_DAILY` explícitamente.
- **Resiliencia**: hasta 3 reintentos en 429/5xx con espera exponencial 1/2/4 s + jitter y `Retry-After` respetado; cortacircuitos que abre 60 s tras 5 fallos consecutivos — el análisis siempre continúa con bandera `VT_NO_DISPONIBLE`.
- **Caché** de veredictos reales por tipo: archivos 7 días; URLs/dominios/IPs 24 h; desconocidos (404) 1 hora. Los fallos transitorios **nunca** se cachean.
- **Presupuesto** de 10 consultas externas por correo (`presupuesto_nuevo` compartido por el consumidor); al agotarse, `VT_PRESUPUESTO_AGOTADO` sin llamada.
- **Subida/envío opt-in**: `subir_archivo` (`POST /files`) y `enviar_url_desconocida` (`POST /urls`) no emiten ninguna petición mientras `VT_UPLOAD_UNKNOWN`/`VT_SUBMIT_UNKNOWN_URLS` estén apagados.

```python
from src.level2_agent.virustotal import ConfigVT, consultar_archivo, presupuesto_nuevo

config = ConfigVT.desde_entorno()               # VT_API_KEY, VT_TIER, ...
presupuesto = presupuesto_nuevo(config)          # 10 consultas por correo
resultado = consultar_archivo(sha256, config=config, presupuesto=presupuesto)
resultado.clasificacion                          # maliciosa / sospechosa / limpia / desconocida
resultado.banderas                               # p.ej. VT_ADJ_SOSPECHOSO (catálogo VT)
```

Variables de entorno (ver `.env.example`): `VT_API_KEY`, `VT_TIER` (`public`|`premium`), `VT_RPM`, `VT_DAILY`, `VT_MAX_POR_CORREO`, `VT_UPLOAD_UNKNOWN`, `VT_SUBMIT_UNKNOWN_URLS`, `VT_UMBRAL_MALICIOSA`, `VT_UMBRAL_SOSPECHOSA`, `VT_UMBRAL_LIMPIA`.

> **Aviso de licencia (uso público/demostración)**: la API pública de VirusTotal tiene cuotas estrictas y **prohibición de uso comercial**; el modo `public` (4/min, 500/día) es solo para demostración y pruebas. Cualquier uso productivo requiere una clave premium propia y la responsabilidad de cumplir los términos del servicio.

```powershell
# Pruebas del módulo (84 con este filtro — 98 en total con test_configuracion.py; sin red real)
python -m pytest tests/unit/ -k "vt or clasificacion or limitador or cache_presupuesto"
```

### Motor de Decisión (`decision/`, spec 008)

Motor determinista y explicable que produce el veredicto final del pipeline. Consumido por la spec 009.

1. **Reglas duras R1–R5** (se evalúan primero; la primera que aplica fija `malicioso`):
   - R1: hash de adjunto con VT `maliciosa` → Crítico
   - R2: URL con VT `maliciosa` → Crítico
   - R3: dominio con VT `maliciosa` → Alto
   - R4: SPF+DKIM+DMARC fallan + dominio parecido/nombre suplanta → Alto
   - R5: macro/ejecutable en adjunto cifrado + remitente no autenticado → Crítico

2. **Tabla de decisión** (si ninguna regla aplicó): 6 filas que combinan `score_final`, la confirmación del agente y las verificaciones incompletas. La palabra **"seguro" jamás aparece** como veredicto (Art. V.1). Si una verificación obligatoria quedó incompleta, el veredicto es `revision_manual` (nunca `sin_indicadores`).

```python
from src.level2_agent.decision import evaluar_veredicto, EntradaMotor

resultado = evaluar_veredicto(entrada)
resultado.veredicto          # malicioso / sospechoso / revision_manual / sin_indicadores
resultado.nivel_severidad    # Critico / Alto / Medio / Bajo
resultado.ruta               # reglas / heuristica / ia
resultado.reglas_aplicadas   # [{"id": "R1", ...}]
```

```powershell
# Pruebas del módulo (76 con este filtro — sin red real, sin I/O)
python -m pytest tests/unit/ -k "dec"
```

### Agente de IA Sin Estado (`agente/`, spec 009)

Agente que desempata la zona gris (score 30–75) con una única llamada al modelo LLM, validación estricta de salida y resistencia a inyección de prompts.

1. **Entrada estructurada**: recibe toda la evidencia calculada (banderas, autenticación, URLs, adjuntos, VT, score) — no parsea el correo crudo.
2. **Única herramienta**: `busqueda_vectorial` (RAG de solo lectura). Se retiraron `check_ip_reputation` y `jira_integration` del ReAct.
3. **Triple defensa anti-inyección**: (a) sanitización de PII, (b) delimitadores `<correo>…</correo>` con declaración de no confianza, (c) prompt declarativo de seguridad.
4. **Salida validada**: esquema `SalidaAgente` (Pydantic) con longitudes máximas. Si la validación falla, 1 reintento; si persiste, `validacion_fallida`.
5. **Tope diario**: contador `ContadorLLM` (MongoDB con TTL, fallback in-memory). Al superar `LLM_MAX_DIARIO` (default 100), la zona gris va a `revision_manual` sin llamar al modelo.
6. **Adapter**: `ModeloLLM` Protocol + `GeminiAdapter`. Modelo configurable vía `LLM_MODELO` env var. Tests usan `ModeloDoble` (cero llamadas reales).

```python
from src.level2_agent.agente import consultar_agente, EntradaAgente

resultado = consultar_agente(entrada)
resultado.confirmacion_agente  # True/False/None
resultado.razon               # exito / tope_superado / validacion_fallida
```

```powershell
# Pruebas del módulo (14 — sin modelo real, sin red)
python -m pytest tests/unit/ -k "agt"
```

## Dependencias principales

- **LangChain / LangGraph** — Framework de agentes y cadenas LLM
- **Google Generative AI** — Modelo Gemini (embeddings + chat)
- **MongoDB Atlas** — Vector store (RAG)
- **Google API Client** — Integración Gmail
- **Pydantic** — Modelos de datos con validación
- **Hypothesis** — Pruebas basadas en propiedades (enmascarado PII, spec 002)
- **tldextract** — Dominio registrable vía PSL embebida (banderas, spec 003)
- **httpx** — Cliente HTTP asíncrono (cliente VirusTotal, spec 006)

Ver `requirements.txt` para la lista completa.

## Comando de calidad

El repositorio tiene compuertas automáticas que validan la constitución en cada cambio:

```powershell
python scripts/verify.py
```

Ejecuta 8 compuertas: longitud de archivos (≤500 líneas), nombre de rama, cobertura (≥80 % líneas y ramas), trazabilidad AC→prueba, secretos (`gitleaks`), dependencias (`pip-audit`), lint (`ruff`) y tipos (`mypy --strict`). Exit 0 si todas las obligatorias pasan; 1 si alguna falla. En Unix: `make verify`.

**Trazabilidad**: cada prueba se marca con `@pytest.mark.ac("AC-XXX-NN")` para asociarla a un criterio de aceptación (Art. II.6 de la constitución). `python scripts/check_trazabilidad_ac.py --spec specs/NNN-*/spec.md` lista los AC sin prueba.

**Alcance actual** (spec 000): las compuertas de lint, tipos y cobertura se aplican sobre `scripts/` y `tests/unit/` (código nuevo). Su extensión a `src/` se habilita progresivamente en las specs 01–15 que refactorizan el código existente. `gitleaks` y `pip-audit` sí cubren todo el repo/entorno.

**CI**: `.github/workflows/verify.yml` ejecuta `python scripts/verify.py` en cada pull request y bloquea el merge si falla.
