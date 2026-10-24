# Contrato: API pública del paquete `src.level2_agent.adjuntos`

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Modelo de datos**: [data-model.md](./data-model.md)

Contrato de la librería que exige el Art. 3.7 ("las dependencias externas se acceden
por interfaces") y que consumen las specs 006 (VirusTotal por hash) y 008 (reglas
duras del motor de decisión). Es un contrato **de Python** (no hay endpoints ni CLI
en esta spec).

## API de nivel módulo

```python
from src.level2_agent.adjuntos import (
    analizar_adjunto,      # función principal
    AnalisisAdjunto,       # modelo de salida (Pydantic)
    ConfigAdjuntos,        # configuración (Pydantic); .desde_entorno() lee el env
    ConfiguracionError,    # error propio ante config inválida (fail-fast)
    CATALOGO_ADJUNTOS,     # dict[codigo, (severidad, puntos)] — catálogo 5.3
)
```

## `analizar_adjunto`

```python
def analizar_adjunto(
    nombre: str,
    tipo_declarado: str,
    payload: bytes,
    config: ConfigAdjuntos | None = None,   # None → ConfigAdjuntos.defecto()
) -> AnalisisAdjunto:
    """Analiza estáticamente un adjunto en memoria (FR-001..FR-006).

    Nunca escribe a disco, nunca ejecuta, nunca abre con aplicaciones del
    sistema, nunca usa red. Nunca lanza por datos de entrada: toda entrada
    hostil (vacía, truncada, nombre con `..` o rutas) produce un resultado
    con hashes correctos y las banderas que apliquen (AC-ADJ-06).
    """
```

### Semántica de la llamada

| Aspecto | Contrato |
|---|---|
| `nombre` | nombre original del adjunto; se usa **solo** para reglas de extensión (D4); jamás para abrir rutas |
| `tipo_declarado` | `Content-Type` de la parte MIME; vacío = no comparar (D5) |
| `payload` | bytes ya decodificados en memoria (no se copian a disco ni se re-leen) |
| `config` | `None` usa los defaults del M05 (constantes nombradas) |
| Excepciones | **solo** `ConfiguracionError` (constructor de config). Por datos: nunca lanza (D14) |
| Determinismo | misma entrada + misma config → misma salida (sin hora, azar ni red) |
| Efectos | ninguno observable fuera del objeto devuelto (AC-ADJ-05) |

### Garantías de seguridad (las verifican las pruebas)

1. **En memoria**: cero escrituras a disco; cero ejecuciones; cero llamadas a red
   (verificación AST del paquete + tmpdir vacío tras analizar: AC-ADJ-05).
2. **Límites**: el análisis de zip se aborta al superar `limite_entradas_zip`,
   `limite_descomprimido_zip` o `ratio_maximo_zip` **durante** la lectura por bloques
   (no se materializa el exceso: SC-002/AC-ADJ-04).
3. **Fallar hacia revisar**: archivo que debía inspeccionarse y no pudo →
   `ADJ_ARCHIVO_SOSPECHOSO`, nunca silencio (Art. V.1).
4. **PII**: los `detalles` no contienen nombres de archivo completos ni direcciones
   (Art. V.4).

## `AnalisisAdjunto` (campos públicos)

Ver [data-model.md](./data-model.md#analisisadjunto-pydantic--salida-de-analizar_adjunto)
para el detalle de validación. Resumen: `nombre`, `tipo_declarado`, `tipo_real`,
`tamano_bytes`, `sha256` (hex64), `md5` (hex32), `sha1` (hex40),
`banderas: list[BanderaAdjunto]` (orden estable = catálogo 5.3, sin duplicados),
`detalles: list[str]`.

### Códigos de bandera emitibles (catálogo 5.3)

`ADJ_EXTENSION_RIESGO` (alta/20), `ADJ_DOBLE_EXTENSION` (alta/20),
`ADJ_TIPO_NO_COINCIDE` (alta/15), `ADJ_MACRO` (alta/20), `ADJ_ENLACE_EXTERNO`
(media/10), `ADJ_PDF_ACTIVO` (media/10), `ADJ_CIFRADO` (media/12),
`ADJ_ARCHIVO_SOSPECHOSO` (alta/15), `ADJ_HTML` (media/10).
`VT_ADJ_SOSPECHOSO` (alta/25) **no** la emite esta spec: es de la 006.

## `ConfigAdjuntos` (variables de entorno)

Ver [data-model.md](data-model.md#configadjuntos-pydantic--inyectado-o-desde_entorno)
para la tabla completa. Todas son opcionales; los defaults del M05 se documentan en
`.env.example`. Formato inválido → `ConfiguracionError`.

## Protocolos (interfaces de sustitución en pruebas)

```python
class AnalizadorOffice(Protocol):
    def analizar(self, payload: bytes) -> HallazgosOffice:
        """Macros/enlaces externos en Office; nunca lanza (degrada a hallazgos)."""
```

Implementación real `OlevbaOffice` (oletools/olevba, D6); las pruebas del motor
usan un doble (Art. II.5: cero red, cero librerías opacas en CI cuando se prueba el
registry).

## Consumo previsto (fuera de alcance de esta spec)

```python
# Spec 006 — consulta VT por hash (nunca sube el archivo: FR-007)
resultado = analizar_adjunto(adjunto.nombre, adjunto.tipo_declarado, payload)
hash_vt = resultado.sha256                      # ← clave de la consulta

# Spec 008 — reglas duras con puntos del catálogo
puntos_adj = sum(b.puntos for b in resultado.banderas)
```

El "cose" de `Adjunto` (spec 002) + `AnalisisAdjunto` (esta spec) lo deciden las
specs consumidoras; aquí no se toca `models.py` (D15).
