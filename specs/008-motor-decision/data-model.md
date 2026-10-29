# Data Model: Motor de Decisión Determinista (spec 008)

## Entidades

### EntradaMotor (input del motor)

Agrupa todos los insumos que el orquestador del pipeline recolecta antes de
llamar al motor. Pydantic BaseModel, validado.

| Campo | Tipo | Origen (spec) | Descripción |
|---|---|---|---|
| `email_data` | `EmailData` | 002 | Correo normalizado (para R4: dominio, nombre visible) |
| `score_final` | `ScoreFinal` | 007 | Score compuesto (clasificador + banderas) |
| `banderas_cabeceras` | `list[Bandera]` | 003 | Banderas de cabeceras evaluadas |
| `estados_autenticacion` | `EstadosAutenticacion` | 003 | SPF/DKIM/DMARC |
| `resultado_urls` | `ResultadoURLs \| None` | 004 | Análisis de URLs (banderas, VT) |
| `resultado_adjuntos` | `list[AnalisisAdjunto]` | 005 | Análisis de adjuntos |
| `resultados_vt` | `list[ResultadoVT]` | 006 | Veredictos VirusTotal |
| `confirmacion_agente` | `bool \| None` | 009 | `None`=no consultado; `True`=phishing; `False`=no phishing |
| `verificaciones_incompletas` | `list[VerificacionIncompleta]` | orquestador | Pre-computadas por quien llama al motor |

### VerificacionIncompleta

| Campo | Tipo | Descripción |
|---|---|---|
| `tipo` | `Literal["vt_adjunto", "vt_url", "vt_dominio", "vt_ip", "expansion_url"]` | Qué verificación falló |
| `razon` | `str` | E.g. "VT_NO_DISPONIBLE", "VT_PRESUPUESTO_AGOTADO", "limite_excedido" |

### VeredictoMotor (output del motor)

| Campo | Tipo | Descripción |
|---|---|---|
| `veredicto` | `Literal["malicioso", "sospechoso", "revision_manual", "sin_indicadores"]` | Veredicto final (FR-005) |
| `score_final` | `int` | Score 0–100 que entró al motor |
| `nivel_severidad` | `Literal["Critico", "Alto", "Medio", "Bajo"]` | Según tabla M09.1 |
| `ruta` | `Literal["reglas", "heuristica", "ia"]` | Cómo se decidió (FR-005) |
| `reglas_aplicadas` | `list[str]` | E.g. `["R1"]`, `[]` si ninguna |
| `banderas` | `list[Bandera]` | Banderas que influyeron |
| `verificaciones_incompletas` | `list[VerificacionIncompleta]` | Las que pasaron (para transparencia) |

### ReglaDura (interna)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `Literal["R1", "R2", "R3", "R4", "R5"]` | Identificador de la regla |
| `descripcion` | `str` | Descripción humana |
| `severidad` | `Literal["Critico", "Alto"]` | R1/R2/R5→Crítico; R3/R4→Alto (M09.1) |

### FilaTabla (interna)

| Campo | Tipo | Descripción |
|---|---|---|
| `condicion` | `Callable[..., bool]` | Predicado sobre (score, agente, verificaciones, banderas) |
| `veredicto` | `Veredicto` | Veredicto si la condición aplica |
| `severidad` | `NivelSeveridad` | Severidad correspondiente |
| `ruta` | `Ruta` | Ruta de decisión |

## Constantes

| Nombre | Valor | Origen |
|---|---|---|
| `UMBRAL_BAJO` | `30` | M09 (score < 30 → zona baja) |
| `UMBRAL_ALTO` | `76` | M09 (score >= 76 → malicioso directo) |
| `REGLAS_DURAS` | `[R1, R2, R3, R4, R5]` | M09 (orden de evaluación) |
| `TABLA_DECISION` | 6 filas | M09 (FR-002) |

## Relaciones

```
EntradaMotor ──→ evaluar_veredicto() ──→ VeredictoMotor
     │                                          │
     ├── score_final (ScoreFinal, spec 007)      ├── veredicto (Literal)
     ├── banderas_cabeceras (spec 003)           ├── nivel_severidad
     ├── resultado_urls (spec 004)               ├── ruta
     ├── resultado_adjuntos (spec 005)           ├── reglas_aplicadas
     ├── resultados_vt (spec 006)                ├── banderas
     ├── confirmacion_agente (spec 009)          └── verificaciones_incompletas
     └── verificaciones_incompletas
```

## Invariantes

1. `VeredictoMotor.veredicto` nunca es `"seguro"` (FR-006, Art. V.1).
2. Si `verificaciones_incompletas` no está vacío, `veredicto` es
   `"revision_manual"` (FR-003, AC-DEC-03).
3. Si una regla dura aplicó, `veredicto` es `"malicioso"` independientemente
   de `confirmacion_agente` (FR-004, AC-DEC-07).
4. `score_final` está en [0, 100] (invariante de ScoreFinal, spec 007).
5. `evaluar_veredicto` es determinista: mismo `EntradaMotor` → mismo
   `VeredictoMotor` (AC-DEC-04).
