# Contract: Persistencia y Métricas de Análisis

**Spec**: 011 · **Date**: 2026-10-30

## §1 — guardar_analisis

```python
def guardar_analisis(
    analisis: AnalisisPersistido,
    *,
    repo: RepositorioAnalisis | None = None,
) -> str:
    """Persiste un análisis en MongoDB.

    Pre-condición: analisis.correo_enmascarado no contiene htmlBody ni contenido.
    Post-condición: documento insertado en phishguard.analyses con TTL.
    Retorna: message_id del análisis guardado.
    """
```

**Invariante I1/I2**: el documento persistido jamás contiene `htmlBody` ni `contenido`.

## §2 — calcular_metricas

```python
def calcular_metricas(
    analisis: list[AnalisisPersistido],
    *,
    tz: str = "America/Bogota",
    inicio: date | None = None,
    fin: date | None = None,
) -> Metricas:
    """Calcula métricas sobre una lista de análisis (función pura).

    Pre-condición: analisis es una lista (puede estar vacía).
    Post-condición: Metricas con todos los campos calculados.
    """
```

**Invariante I3**: `por_dia` tiene un elemento por cada día del rango.
**Invariante I5**: `tasa_falsos_positivos` es `None` si no hay retroalimentación.

## §3 — sembrar_datos

```python
def sembrar_datos(
    *,
    repo: RepositorioAnalisis,
    ahora: datetime | None = None,
) -> int:
    """Genera 100 análisis deterministas y los persiste.

    Pre-condición: repo es un RepositorioAnalisis válido.
    Post-condición: exactamente 100 docs con origen="siembra".
    Idempotente: borra siembra previa antes de insertar.
    Retorna: número de documentos insertados (100).
    """
```

**Invariante I4**: ejecutar 2 veces deja exactamente 100 docs con `origen="siembra"`.

## §4 — borrar_analisis

```python
def borrar_analisis(
    message_id: str,
    *,
    repo: RepositorioAnalisis,
    cache_vt: RepositorioCacheVT | None = None,
) -> bool:
    """Elimina un análisis y su caché VT asociada.

    Pre-condición: message_id no vacío.
    Post-condición: documento eliminado de analyses + entradas vt_cache.
    Retorna: True si se eliminó, False si no existía.
    """
```

## §5 — RepositorioAnalisis (Protocol)

```python
class RepositorioAnalisis(Protocol):
    def guardar(self, doc: dict) -> str: ...
    def buscar(self, message_id: str) -> dict | None: ...
    def listar(self, filtro: dict) -> list[dict]: ...
    def borrar(self, message_id: str) -> bool: ...
    def contar(self, filtro: dict) -> int: ...
```

## §6 — RepositorioCacheVT (Protocol)

```python
class RepositorioCacheVT(Protocol):
    def borrar_por_message_id(self, message_id: str) -> int: ...
```
