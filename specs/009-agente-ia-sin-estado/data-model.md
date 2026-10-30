# Data Model: Agente de IA Sin Estado (spec 009)

## Entidades

### EntradaAgente (input del agente)

| Campo | Tipo | Origen (spec) | Descripción |
|---|---|---|---|
| `email_data` | `EmailData` | 002 | Correo normalizado (para texto del correo) |
| `score_final` | `ScoreFinal` | 007 | Score compuesto |
| `banderas_cabeceras` | `list[BanderaActivada]` | 003 | Banderas de cabeceras |
| `estados_autenticacion` | `EstadosAutenticacion` | 003 | SPF/DKIM/DMARC |
| `resultado_urls` | `ResultadoURLs \| None` | 004 | Análisis de URLs |
| `resultado_adjuntos` | `list[AnalisisAdjunto]` | 005 | Análisis de adjuntos |
| `resultados_vt` | `list[ResultadoVT]` | 006 | Veredictos VirusTotal |

### SalidaAgente (output validado del modelo)

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `resumen` | `str` | max 500 chars | Resumen ejecutivo |
| `analisis_tecnico` | `str` | max 2000 chars | Evaluación técnica forense |
| `es_phishing` | `bool` | — | Opinión del agente |
| `indicadores_phishing` | `list[str]` | max 10 items, cada uno max 200 chars | Patrones de riesgo |
| `nivel_severidad` | `Literal["Bajo","Medio","Alto","Crítico"]` | — | Severidad opinada |
| `justificacion_veredicto` | `str` | max 1000 chars | Justificación citando NIST/OWASP |

### ResultadoAgente (output del orquestador)

| Campo | Tipo | Descripción |
|---|---|---|
| `salida` | `SalidaAgente \| None` | None si falló validación o tope superado |
| `confirmacion_agente` | `bool \| None` | `True`=phishing, `False`=no phishing, `None`=no consultado |
| `reintentos` | `int` | 0, 1 o 2 (0=éxito primer intento, 1=éxito reintento, 2=falló) |
| `llamadas_modelo` | `int` | 0, 1 o 2 llamadas al modelo |
| `razon` | `str` | "exito", "tope_superado", "validacion_fallida" |

### ContadorLLM (interno)

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha` | `date` | Día del conteo |
| `conteo` | `int` | Número de llamadas en ese día |
| `expira_en` | `datetime` | TTL para MongoDB |

## Constantes

| Nombre | Valor | Origen |
|---|---|---|
| `LLM_MAX_DIARIO` | env var, default 100 | M07 (FR-007) |
| `LLM_MODELO` | env var, default "models/gemini-2.5-flash-lite" | M07 (FR-008) |
| `LLM_TEMPERATURA` | `0` | M07 |
| `DELIM_CORREOInicio` | `"<correo>"` | M07 |
| `DELIM_CORREO_FIN` | `"</correo>"` | M07 |
| `MAX_REINTENTOS` | `1` | M07 (AC-AGT-03) |
| `LIMITE_RESUMEN` | `500` | M07 |
| `LIMITE_ANALISIS` | `2000` | M07 |
| `LIMITE_INDICADORES` | `10` | M07 |
| `LIMITE_JUSTIFICACION` | `1000` | M07 |

## Relaciones

```
EntradaAgente ──→ consultar_agente() ──→ ResultadoAgente
     │                                          │
     ├── score_final (ScoreFinal, spec 007)      ├── salida (SalidaAgente | None)
     ├── banderas_cabeceras (spec 003)          ├── confirmacion_agente (bool | None)
     ├── resultado_urls (spec 004)              └── razon (str)
     ├── resultado_adjuntos (spec 005)
     ├── resultados_vt (spec 006)
     └── email_data (spec 002)

ResultadoAgente.confirmacion_agente ──→ EntradaMotor.confirmacion_agente (spec 008)
```

## Invariantes

1. Si `ContadorLLM.conteo >= LLM_MAX_DIARIO`, `ResultadoAgente.salida` es `None`
   y `ResultadoAgente.razon` es "tope_superado" (FR-007, AC-AGT-05).
2. Si la salida del modelo no valida como `SalidaAgente` tras 1 reintento,
   `ResultadoAgente.salida` es `None` y `ResultadoAgente.razon` es
   "validacion_fallida" (FR-004, AC-AGT-03).
3. La lista de herramientas del ReAct es exactamente `[busqueda_vectorial]`
   (FR-002, AC-AGT-01).
4. La consulta al RAG usa `enmascarar_texto(texto_correo)`, nunca el texto
   crudo (FR-005).
5. Ninguna prueba llama al modelo real (AC-AGT-06).
