# Contrato: `calcular_score_final` (API pública del paquete scoring)

**Spec**: 007-scoring-genetico · **Rama**: `feature/scoring-genetico` · **Versión del contrato**: 1

Consumidores: `src/level2_agent/agent.py` (cableado), pruebas unitarias, futura spec 008 (motor de decisión). Idioma de mensajes: español.

## 1. Superficie pública (`src/level3_logic/scoring/__init__.py`)

```python
from src.level3_logic.scoring import (
    calcular_score_final,   # fachada de composición
    ScoreFinal,             # modelo pydantic de salida
    BanderaScoring,         # trazabilidad agregada de banderas
    ConfigScoring,          # configuración (desde_entorno)
    DependenciasScoring,    # puertos inyectables (producción por defecto)
    ScoringError,           # excepción base del paquete
    PesosError,             # subclase: pesos ausentes/inválidos
)
from src.level3_logic.pesos import cargar_pesos, PesosGeneticos
```

## 2. Firma

```python
def calcular_score_final(
    email_data: EmailData,
    config: ConfigScoring | None = None,        # None ⇒ ConfigScoring.desde_entorno()
    deps: DependenciasScoring | None = None,    # None ⇒ defaults de producción
    adjuntos_analizados: Sequence[AnalisisAdjunto] = (),
) -> ScoreFinal
```

Máximo 5 parámetros (Art. III.2). Función pura dados los insumos y los pesos en cache.

## 3. Semántica (orden exacto)

1. `pesos = cargar_pesos(config.ruta_pesos)` → versiona (`version_pesos = pesos.version`).
2. Genético: `genetic_logic.evaluate(datos_legados(email_data), config=ConfigGenetico(pesos, listas))` ⇒ `score_genetico` (con sesgo `pesos.sesgo`, FR-003) e `genes_implicados` (FR-004/FR-005 aplicados).
3. Banderas de cabeceras: `banderas.evaluar_banderas(email_data, ahora=deps.ahora, cliente_rdap=deps.cliente_rdap)` ⇒ `puntos_totales` (ya ≤ 60, spec 003).
4. URLs: `analisis_urls.analizar_urls(email_data, deps=deps.deps_urls)` ⇒ `Σ banderas[].puntos` (catálogo 5.2).
5. Adjuntos: `Σ adjuntos_analizados[].banderas[].puntos` (catálogo 5.3); vacío en el pipeline actual (research D7).
6. `puntos_banderas = min(TOPE_PUNTOS_BANDERAS, suma)` — constante importada de `banderas/modelos.py` (nunca redefinida).
7. `score_final = min(100, round(score_genetico + puntos_banderas))` (entero).
8. `banderas` (BanderaScoring) agrega las tres fuentes con su origen, en orden estable cabeceras → urls → adjuntos.

**Monotonicidad (AC-SCO-02)**: como `puntos_banderas ≥ 0` y `min(100,·)` es no decreciente, activar una bandera adicional **nunca** reduce `score_final`.

## 4. Errores

| Condición | Excepción | Comportamiento del pipeline (agent.py) |
|---|---|---|
| `data/pesos/pesos_v1.json` ausente, ilegible o con schema inválido | `PesosError` | fallback actual: `SCORE_FALLBACK=50.0` (ruta agente) + log error; `version_pesos="indeterminada"` |
| `ConfigScoring` inválida (env malformada) | `ScoringError` | ídem |
| Fallo de puerto externo (RDAP caído, expansión abortada) | **no lanza**: los módulos 003/004 degradan por diseño | banderas/url points ausentes; el veredicto lo decide la spec 008 (Art. V.1) |

## 5. Configuración (env)

| Variable | Efecto | Default |
|---|---|---|
| `DOMINIOS_PROPIOS` | dominios corporativos (genes 0 y 28) | vacío |
| `DOMINIOS_PROVEEDORES_CONFIANZA` | proveedores de confianza (genes 0 y 28) | lista constante D5 |
| `RUTA_PESOS` | ruta alternativa al archivo de pesos | `data/pesos/pesos_v1.json` |

## 6. Ejemplo canónico

```python
resultado = calcular_score_final(email)
# ScoreFinal(score_final=82, score_genetico=41.75, puntos_banderas=40,
#            version_pesos="pesos_v1", genes_implicados=[...], banderas=[...])
report["score"] = resultado.score_final
report["score_genetico"] = resultado.score_genetico
report["version_pesos"] = resultado.version_pesos
```

## 7. Compatibilidad

- `genetic_logic.evaluate(dict)` conserva su firma aditiva (`config=` keyword-only) y su shape de retorno (`score`, `genes_implicados`, `suma_lineal_ag`) + `version_pesos` nuevo; el runner legado `tests/test_pipeline.py` sigue funcionando con defaults (research D10: se ajusta solo la metadata `_test` si la ruta cambia, con aprobación del usuario).
- Sin dependencias nuevas; sin cambios en `banderas/`, `analisis_urls/`, `adjuntos/`, `models.py` ni `normalizacion/`.
