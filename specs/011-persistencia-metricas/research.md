# Research: Persistencia y Métricas de Análisis

**Spec**: 011 · **Date**: 2026-10-30

## D1 — Estructura del paquete

**Decisión**: `src/level2_agent/persistencia/` con 6 módulos (`modelos.py`, `repositorio.py`, `metricas.py`, `siembra.py`, `borrado.py`) + `__init__.py`.

**Rationale**: Sigue el patrón de specs 003–010. Separación clara: modelos (datos), repositorio (I/O), métricas (cálculo puro), siembra (datos fijos), borrado (operación).

**Alternativas**: Un solo archivo → superaría 500 líneas.

## D2 — Repository pattern sobre MongoDB

**Decisión**: `RepositorioAnalisis` class con métodos `guardar(analisis)`, `buscar(message_id)`, `listar(filtros)`, `borrar(message_id)`, `contar(filtros)`, `agregar_por_dia(inicio, fin, tz)`. Inyecta `coleccion` (pymongo Collection) para testabilidad. Tests usan `RepositorioDoble` (dict in-memory).

**Rationale**: Repository pattern (Art. III.5) desacopla lógica de negocio de MongoDB. Permite dobles sin conexión real.

**Alternativas**: Acceso directo a pymongo → difícil de testear sin MongoDB real.

## D3 — No persistir HTML ni adjuntos (FR-002)

**Decisión**: Antes de persistir, se aplica `enmascarar_para_terceros()` (spec 002) al `EmailData`. Se excluyen campos `htmlBody` (ya `exclude=True` en Pydantic) y `adjuntos[].contenido`. Se verifica con test que el documento persistido no contiene claves `htmlBody` ni `contenido`.

**Rationale**: FR-002 explícito. Art. V.4: datos personales enmascarados.

**Alternativas**: Ninguna — es requisito duro.

## D4 — Métricas como función pura sobre lista

**Decisión**: `calcular_metricas(analisis: list[AnalisisPersistido], *, tz, inicio, fin) -> Metricas`. Recibe la lista de análisis (ya leída del repo), retorna métricas calculadas. Es una función pura — cero I/O, cero estado. Facilita tests con datos de siembra sin MongoDB.

**Rationale**: Separar cálculo de I/O. Los datos de siembra se pueden pasar directamente.

**Alternativas**: Agregaciones MongoDB → más eficientes pero difíciles de testear y dependientes de la base.

## D5 — Siembra determinista (FR-006)

**Decisión**: `sembrar_datos(repositorio) -> int`. Genera exactamente 100 análisis por fórmula: 55 `sin_indicadores`, 15 `sospechoso`, 30 `malicioso`. 60 resueltos por heurística (ruta `heuristica`), 40 con IA (ruta `ia`). Fechas distribuidas en los últimos 90 días en zona `America/Bogota`.>`. Marcados con `origen="siembra"`. Idempotente: borra documentos de siembra previos antes de insertar.

**Rationale**: FR-006 exige determinismo (sin aleatoriedad). Fórmula: `veredicto = ["sin_indicadores"]*55 + ["sospechoso"]*15 + ["malicioso"]*30`.

**Alternativas**: JSON fixture → más frágil, difícil de mantener.

## D6 — Zona horaria America/Bogota

**Decisión**: Usar `pytz.timezone("America/Bogota")` para agrupar `por_dia`. Días en cero se rellenan iterando el rango completo. Tests/Tests con rangos 7, 30 y 90 días.

**Rationale**: AC-PER-04 exige cambio de zona horaria. `pytz` ya está instalado.

**Alternativas**: `zoneinfo` (Python 3.9+) → pytz ya instalado y usado en el proyecto.

## D7 — Borrado con caché VT asociada (FR-005)

**Decisión**: `borrar_analisis(message_id, *, repo, cache_vt) -> bool`. Elimina el documento de `analyses` y busca en `vt_cache` por `message_id` (campo añadido al caché en spec 006) para eliminar entradas relacionadas.

**Rationale**: AC-PER-07: borrar un análisis elimina documento + caché.

**Alternativas**: Solo borrar análisis → caché huérfana.

## D8 — Scope fence

**Decisión**: NO se modifica: `src/level2_agent/decision/` (import), `src/level2_agent/agente/` (import), `src/level2_agent/acciones/` (import), `src/level2_agent/virustotal/` (import solo para tipo de caché). Se modifica: `src/gmail_integration/gmail_poller.py` (wiring: llamar `guardar` tras cada análisis).

**Rationale**: Art. VI.1: solo lo que pide la spec.
