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
│   │   ├── analisis_urls/      # Análisis y expansión de URLs (spec 004, M04b)
│   │   │   ├── motor.py        # analizar_urls (API pública, sin wiring aún)
│   │   │   ├── expansion.py    # Acortadores con validación SSRF por salto
│   │   │   ├── banderas.py     # Catálogo 5.2 (13 códigos de URL)
│   │   │   ├── ssrf.py         # Redes FR-004 + is_global por hop
│   │   │   └── configuracion.py # Listas configurables vía .env
│   │   └── tools/
│   │       ├── __init__.py     # Retriever RAG vectorial
│   │       ├── ip_reputation.py # Consulta VirusTotal
│   │       └── jira_integration.py # Creación de tickets Jira
│   ├── level3_logic/           # Algoritmo genético
│   │   └── genetic_logic.py    # 32 genes de detección
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

## Dependencias principales

- **LangChain / LangGraph** — Framework de agentes y cadenas LLM
- **Google Generative AI** — Modelo Gemini (embeddings + chat)
- **MongoDB Atlas** — Vector store (RAG)
- **Google API Client** — Integración Gmail
- **Pydantic** — Modelos de datos con validación
- **Hypothesis** — Pruebas basadas en propiedades (enmascarado PII, spec 002)

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
