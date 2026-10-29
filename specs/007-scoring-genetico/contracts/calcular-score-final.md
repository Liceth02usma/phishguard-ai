# Contrato: `calcular_score_final` (API pública del paquete scoring)

**Spec**: 007-scoring-genetico · **Rama**: `feature/scoring-genetico` · **Versión**: 2 (clasificador lineal)

## 1. Superficie pública (`src/level3_logic/scoring/__init__.py`)

```python
from src.level3_logic.scoring import (
    calcular_score_final,
    ScoreFinal,
    BanderaScoring,
    ConfigScoring,
    DependenciasScoring,
    ScoringError,
    ModeloError,
)
from src.level3_logic.modelo import cargar_modelo, ClasificadorLineal
```

## 2. Firma

```python
def calcular_score_final(
    email_data: EmailData,
    config: ConfigScoring | None = None,
    deps: DependenciasScoring | None = None,
    adjuntos_analizados: Sequence[AnalisisAdjunto] = (),
) -> ScoreFinal
```

## 3. Semántica (8 pasos)

1. `modelo = cargar_modelo(config.ruta_modelo)` → `version_modelo = modelo.version`.
2. Genético: `genetic_logic.evaluate(datos_legados(email_data), config=ConfigGenetico(modelo, listas))` ⇒ `score_clasificador` (con coeficientes del modelo, FR-003) e `genes_implicados` (FR-004/FR-005 aplicados).
3. Banderas: `evaluar_banderas(email_data, ahora=deps.ahora, cliente_rdap=deps.cliente_rdap)` ⇒ `puntos_totales`.
4. URLs: `analizar_urls(email_data, deps=deps.deps_urls)` ⇒ `Σ banderas[].puntos`.
5. Adjuntos: `Σ adjuntos_analizados[].banderas[].puntos` (inyectados, D7).
6. `puntos_banderas = min(TOPE_PUNTOS_BANDERAS, suma)`.
7. `score_final = min(100, round(score_clasificador + puntos_banderas))`.
8. `banderas` (BanderaScoring) agregadas en orden estable.

## 4. Errores

| Condición | Excepción | Fallback en agent.py |
|---|---|---|
| `clasificador_v1.json` ausente/inválido | `ModeloError` | `SCORE_FALLBACK=50.0` + `version_modelo="indeterminada"` |
| `ConfigScoring` inválida | `ScoringError` | ídem |
| Puerto externo caído | degradación interna (003/004) | puntos ausentes; veredicto por 008 |

## 5. Configuración (env)

| Variable | Efecto | Default |
|---|---|---|
| `DOMINIOS_PROPIOS` | genes 0 y 28 | vacío |
| `DOMINIOS_PROVEEDORES_CONFIANZA` | genes 0 y 28 | lista D5 |
| `RUTA_MODELO` | ruta al JSON del modelo | `data/modelo/clasificador_v1.json` |

## 6. Ejemplo canónico

```python
resultado = calcular_score_final(email)
# ScoreFinal(score_final=82, score_clasificador=41.75, puntos_banderas=40,
#            version_modelo="clasificador_v1", genes_implicados=[...], banderas=[...])
```
