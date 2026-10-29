# Contract: Motor de Decisión (spec 008, M09)

## §1 — Función principal

```python
def evaluar_veredicto(entrada: EntradaMotor) -> VeredictoMotor:
    """Motor de decisión determinista (M09).

    1. Evalúa reglas duras R1–R5 en orden; la primera que aplica fija
       veredicto = "malicioso" (FR-001).
    2. Si ninguna regla aplicó, evalúa la tabla de decisión FR-002
       (6 condiciones ordenadas).
    3. Retorna VeredictoMotor con veredicto, score_final, nivel_severidad,
       ruta, reglas_aplicadas, banderas y verificaciones_incompletas.
    """
```

**Propiedades del contrato**:
- **Determinismo**: misma entrada → misma salida (AC-DEC-04).
- **Pureza**: cero I/O, cero estado, cero azar.
- **Fallar hacia revisar**: verificación incompleta → `revision_manual`,
  nunca `sin_indicadores` (FR-003, AC-DEC-03).
- **Regla dura irrevocable**: si R1–R5 aplican, el agente no puede bajar
  el veredicto (FR-004, AC-DEC-07).
- **Sin "seguro"**: el veredicto jamás contiene "seguro" (FR-006, AC-DEC-05).

## §2 — Reglas duras (R1–R5)

| ID | Condición (sobre EntradaMotor) | Severidad |
|---|---|---|
| R1 | Algún `resultados_vt` tiene `clasificacion == "maliciosa"` y `tipo == "archivo"` | Crítico |
| R2 | Algún `resultados_vt` tiene `clasificacion == "maliciosa"` y `tipo == "url"` | Crítico |
| R3 | Algún `resultados_vt` tiene `clasificacion == "maliciosa"` y `tipo == "dominio"` | Alto |
| R4 | `estados_autenticacion` SPF=fail Y DKIM=fail Y DMARC=fail Y (dominio parecido O nombre que suplanta) | Alto |
| R5 | Algún `resultado_adjuntos` tiene bandera `ADJ_MACRO` o `ADJ_EXTENSION_RIESGO` en adjunto cifrado con contraseña, Y remitente no autenticado | Crítico |

**Orden**: R1 → R2 → R3 → R4 → R5. La primera que aplica fija el veredicto.

## §3 — Tabla de decisión (si ninguna regla dura aplicó)

| # | Condición | Veredicto | Severidad | Ruta |
|---|---|---|---|---|
| 1 | `verificaciones_incompletas` no vacío | `revision_manual` | Medio | `heuristica` |
| 2 | `score_final >= 76` | `malicioso` | Alto | `heuristica` |
| 3 | `30 <= score_final <= 75` Y `confirmacion_agente is True` | `malicioso` | Alto | `ia` |
| 4 | `30 <= score_final <= 75` Y `confirmacion_agente is not True` | `sospechoso` | Medio | `heuristica` |
| 5 | `score_final < 30` Y hay bandera media o alta | `sospechoso` | Medio | `heuristica` |
| 6 | `score_final < 30` Y sin banderas medias/altas Y verificaciones completas | `sin_indicadores` | Bajo | `heuristica` |

**Notas**:
- Fila 3: `confirmacion_agente is True` (no `is not False` — `None` no confirma).
- Fila 4: incluye `confirmacion_agente is None` (agente no consultado) y
  `confirmacion_agente is False` (agente dice no phishing).
- Fila 5: "bandera media o alta" = cualquier bandera con severidad `media` o
  `alta` de los catálogos 5.1 (cabeceras), 5.2 (URLs), 5.3 (adjuntos), VT.

## §4 — Severidad (M09.1)

| Veredicto | Condición | Severidad |
|---|---|---|
| `malicioso` | Regla dura R1, R2 o R5 | Crítico |
| `malicioso` | Cualquier otra (tabla fila 2 o 3) | Alto |
| `sospechoso` o `revision_manual` | | Medio |
| `sin_indicadores` | | Bajo |

## §5 — Semántica de `confirmacion_agente`

| Valor | Significado | Cuándo |
|---|---|---|
| `None` | El agente no fue consultado | Score fuera de 30–75, o spec 09 no ejecutada |
| `True` | El agente opina que es phishing | Score en 30–75 y agente respondió afirmativamente |
| `False` | El agente opina que NO es phishing | Score en 30–75 y agente respondió negativamente |

El motor NO invoca al agente. Quien llama al motor (spec 009) decide si
consultar al agente y pasa el resultado.
