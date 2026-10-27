# Research: Scoring Genético con Banderas (spec 007)

**Fecha**: 2026-10-27 · **Rama**: `feature/scoring-genetico`

Fuentes: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md` M10 y D6, `src/level3_logic/genetic_logic.py` (estado actual), APIs de las specs 003/004/005, contrato publicado de la spec 012 (`specs/012-api-rest/contracts/openapi.yaml`), rama paralela `test/conjunto-evaluacion` (spec 015) y `.env.example`.

## D1 — Composición de `puntos_banderas` (catálogos 5.1 + 5.2 + 5.3)

**Decisión**: `puntos_banderas = min(60, puntos_totales_003 + Σ puntos_urls_004 + Σ puntos_adjuntos_005)`, reutilizando la constante `TOPE_PUNTOS_BANDERAS` **importada** de `banderas/modelos.py` (nunca redefinida).

**Rationale**: la spec 007 declara `Depende de: 03, 04, 05` y M10 define `puntos_banderas` como "la suma de los puntos del **catálogo de la sección 5** con tope de 60" — la sección 5 contiene los tres catálogos (5.1 banderas de cabeceras, 5.2 URLs, 5.3 adjuntos). Nota matemática: como los puntos son ≥ 0, `min(60, min(60, a) + b + c) == min(60, a + b + c)`, así que usar el total ya acotado de 003 (`ResultadoBanderas.puntos_totales`) es equivalente y no pierde información.

**Alternativas consideradas**:
- Solo 003 (`puntos_totales` directo): rechazada — ignora los catálogos 5.2/5.3 y haría innecesarias las dependencias 004/005 declaradas en la spec.
- 003 + 004 sin adjuntos: rechazada — sin justificación para excluir 5.3.
- Tope por catálogo y luego suma: rechazada — M10 fija **un** tope global de 60.

## D2 — Fuente y valor por defecto del sesgo `b` (FR-003)

**Decisión**: el sesgo vive **dentro de `data/pesos/pesos_v1.json`** (campo `sesgo`), por defecto **`-1.0`**. Fórmula: `score_genetico = 100 / (1 + e^{-(Σpesos·genes + b)})`. Sin variable de entorno: la configuración del modelo es el archivo versionado (calibrar = publicar `pesos_vN.json`).

**Rationale**: la restricción de la spec es `score_genetico < 30` con 0 genes ⇒ `b < ln(30/70) ≈ -0.847`. Pero el sesgo no puede ser arbitrariamente negativo o hunde también el phishing real: para que un correo como el fixture `malicious.json` (Σ = 2.418) siga por encima del umbral de maldad de M09 (`≥ 76`), se necesita `2.418 + b ≥ 1.157` ⇒ `b ≥ -1.26`. El intervalo factible es `[-1.26, -0.847)`; se elige `b = -1.0` (centro razonable, redondo, deja 0 genes en 26.89 % y el fixture malicious en 80.5 %). El valor queda **[VERIFICAR]** para calibración por curva ROC con el conjunto de M13 (sección "Umbrales" de M10): la calibración posterior se publicaría como nueva versión de pesos, sin tocar umbrales por cuenta propia (AC-SCO-04 es report-only).

**Alternativas consideradas**:
- Variable de entorno `SESGO_*`: rechazada — rompe reproducibilidad y versionado (AC-SCO-03): dos procesos con distinto `.env` darían scores distintos sin cambiar la versión de pesos.
- `b = 0` con normalización posterior: rechazada — no satisface AC-SCO-01 (sigue dando 50 con 0 genes).
- Sesgo -1.5 (márgenes): rechazada — hunde el fixture malicious a 71.5 % (< 76) y provocaría falsos negativos medidos por AC-SCO-04.

## D3 — Pesos versionados en JSON validado (FR-006)

**Decisión**: `data/pesos/pesos_v1.json` con schema Pydantic (`PesosGeneticos` en `src/level3_logic/pesos.py`): `version` (str, identifica "pesos_v1"), `fecha`, `conjunto_entrenamiento`, `semilla`, `sesgo` (float) y `pesos` (exactamente los 32 nombres de `MAPEO_INDICES` → float). Carga con **cache de proceso**; archivo ausente o inválido ⇒ `PesosError` (fallo ruidoso, Art. III.9). El runtime **deja de leer** `PESOS_AG` hardcodeado (FR-006: "los pesos se versionan"); `MAPEO_INDICES` permanece en código (es el orden de los genes, no un peso).

**Rationale**: `VERSION_PESOS = "pesos_v1"` ya existe hardcodeado en `genetic_logic.py` (lo añadió la 015); con el JSON la versión se **deriva del archivo**, eliminando la duplicación. El valor v1 del JSON son literalmente los 32 pesos actuales de `PESOS_AG` (son el "pesos_v1" existente; la spec marca `[VERIFICAR]` los pesos, no los cambia — el reentrenamiento está fuera de alcance). `data/genes.xlsx` sigue **sin cargarse en runtime** (igual que hoy).

**Alternativas consideradas**:
- Mantener `PESOS_AG` en código: rechazada — viola FR-006 ("pesos versionados").
- Cargar el xlsx: rechazada — dependencia nueva y el xlsx es material de exploración, no contrato.
- YAML: rechazada — el proyecto ya versiona JSON (manifestos, fixtures).

## D4 — Coincidencia por palabra completa (FR-004)

**Decisión**: helper `contiene_palabra_completa(palabra, texto)` en `genetic_logic.py` usando regex compilada `(?<!\w)palabra(?!\w)` con `re.IGNORECASE` y palabras escapadas (`re.escape`), en minúsculas; reemplaza el `palabra in texto_lower` de `_contiene_alguna` para todos los detectores de genes léxicos (asunto, cuerpo, URL keywords).

**Rationale**: sin dependencias nuevas; `\b`/lookarounds resuelven "urgente" ⊄ "insurgente" (AC-SCO-06) y también "banco" ⊄ "banco" mal... es decir, mantiene coincidencias legítimas con acentos/puntuación. Compilada una vez a nivel de módulo (rendimiento despreciable, pero limpio).

**Alternativas consideradas**:
- Tokenizar con `split()`: rechazada — falla con puntuación pegada ("urgente," "verify.") y con Unicode variable.
- Librería (`regex`, NLP): rechazada — cero dependencias nuevas.

## D5 — Listas de dominios propios y de confianza (FR-005)

**Decisión**: `ConfigScoring.desde_entorno()` lee `DOMINIOS_PROPIOS` (reutiliza la variable ya publicada por la spec 003, sin duplicar nomenclatura) y la nueva `DOMINIOS_PROVEEDORES_CONFIANZA` (coma-separada; default constante en código con proveedores de correo mayoritarios: gmail/googlemail, outlook/hotmail/live, yahoo, aol, icloud, protonmail/proton.me, mail.com, gmx, zoho, yandex + transaccionales sendgrid.net, mailchimp.com, amazonses.com, postmarkapp.com, sparkpost.com — sobre escribible). Efecto en genes:
- `dominio_externo` (índice 0): solo se activa si el dominio del remitente ≠ dominio del destinatario **y ninguno** de los dos está en (propios ∪ confianza).
- `mismatch_dominio_url` (índice 28): solo si el dominio de la URL difiere del remitente **y** ninguno está en (propios ∪ confianza).

**Rationale**: M10 ("quitar o relativizar `dominio_externo` y `mismatch_dominio_url` usando listas de dominios propios y de proveedores de confianza"); reutiliza la env de 003 para coherencia de operación; los defaults son constantes nombradas (Art. III.6) y sobre escribibles.

**Alternativas consideradas**:
- Ignorar los genes: rechazada — M10 dice "relativizar", no eliminar; se conservan los 32 genes (FR-001).
- Env `DOMINIOS_CONFIANZA` única: rechazada — mezclaría propios con proveedores; la spec pide "listas" (plural) distintas.

## D6 — Cableado en `agent.py` (por qué y hasta dónde)

**Decisión**: `analyze_email()` llama a la nueva fachada `calcular_score_final(email_data)`; la ruta se decide con `score_final` (los umbrales `SCORE_UMBRAL_BAJO=30` / `SCORE_UMBRAL_ALTO=75` **no cambian**); `PhishingReport` gana `score_genetico` y `version_pesos` (campos requeridos por el contrato 012). Si el scoring lanza excepción (pesos ausentes, config inválida), se conserva el fallback actual (`SCORE_FALLBACK=50.0` → ruta agente, que es la de mayor escrutinio) + log de error.

**Rationale**: el contrato **ya publicado** de la spec 012 (`openapi.yaml` schema `Resultado`) exige `score` (= "Score final 0–100"), incluye `score_genetico` ("Aporte del algoritmo genético (spec 007)") y exige `version_pesos`; M10 es una etapa del pipeline; AC-SCO-03 dice "cada análisis guarda la versión usada". Sin cableado, nada del producto produce `score_final`. El cableado mínimo no toca generación de veredictos (008), prompts, Gmail/Jira ni VT (006).

**Alternativas consideradas**:
- Módulo sin cablear (patrón de 003/004/005): rechazada — dejaría el contrato 012 sin implementación y AC-SCO-03 sin cumplir en producto.
- Cablear también la tabla de decisión M09: rechazada — es la spec 008.

## D7 — Puntos de adjuntos (005) por parámetro inyectable

**Decisión**: `calcular_score_final(..., adjuntos_analizados: Sequence[AnalisisAdjunto] = ())`. El motor incluye esos puntos en la suma con tope 60. **El pipeline actual aporta la lista vacía**: `models.Adjunto` (normalización, spec 002) no retiene `payload` (solo `nombre`, `tipo_declarado`, `tamano_bytes`, `sha256`), por lo que en `analyze_email` no hay bytes para llamar a `analizar_adjunto`. Queda documentado como [VERIFICAR]: una spec posterior (006/008 o un cableado en la normalización) podrá pasar el análisis real cuando el payload exista; fuera de alcance de 007 agregar persistencia de adjuntos (Art. VI.1).

**Rationale**: respeta el contrato de 005 sin tocar `models.py` ni `normalizacion/`; las pruebas unitarias sí inyectan `AnalisisAdjunto` reales (con catalogación 5.3) y verifican suma + tope, de modo que el canal está implementado y probado.

**Alternativas consideradas**:
- Agregar campo `adjuntos_analizados` a `EmailData` y que la normalización llame a 005: rechazada — modifica `models.py` y `normalizacion/` (specs ajenas) y exige análisis donde hoy se descarta el payload; alcance de otra spec.
- Ignorar 5.3: rechazada — contradice D1 y las dependencias de la spec.

## D8 — Compuertas de calidad (aditivas)

**Decisión**: `pyproject.toml` gana override `mypy --strict` para `src.level3_logic.scoring*` y `src.level3_logic.pesos`; `scripts/verify.py` añade `--cov=src/level3_logic/scoring`, `--cov=src/level3_logic/pesos`, `--cov=src/level3_logic/genetic_logic` (código modificado entra a la compuerta, Art. II.3) y las rutas nuevas a `RUTAS_CALIDAD_SRC` (ruff) para `scoring/` y `pesos.py`. `genetic_logic.py` **no** entra al scope de ruff/mypy estricto (se modifica funcionalmente conservando su estilo legado; añadirlo dispararía limpieza fuera de alcance — se anota como propuesta futura).

**Rationale**: patrón aditivo ya usado por 003/004/005; mantiene la cobertura global por encima del umbral (la suite actual está en ~89 %).

## D9 — Estructura del paquete y patrones

**Decisión**: `src/level3_logic/scoring/` con `motor.py` (fachada), `modelos.py` (`ScoreFinal`, `BanderaScoring`, `ScoringError`), `configuracion.py` (`ConfigScoring` + `desde_entorno`), `__init__.py` (API pública). `pesos.py` queda **fuera** del paquete (en `src/level3_logic/`) para evitar ciclos de importación (`genetic_logic` lo importa; `scoring.motor` importa `genetic_logic`). Patrones: **Facade** (`calcular_score_final`), **Factory** (`desde_entorno`), inyección de dependencias (puertos de 003/004: `cliente_rdap`, `deps_urls`, reloj `ahora`).

**Rationale**: `genetic_logic.evaluate` sigue siendo la única implementación de extracción de genes (sin duplicación, sin riesgo de divergencia); la fachada compone. Límites: cada archivo < 300 líneas; `genetic_logic.py` modificado < 450.

## D10 — Conflicto de la fixture `ai_agent.json` con SC-001 (Art. II.7)

**Decisión**: la fixture `ai_agent.json` declara `"Score = 50 (zero genes) -> AI Agent route (30-75)"`. Con el sesgo (AC-SCO-01), 0 genes ⇒ 26.89 ⇒ ruta **benigna** (< 30) — el cambio es **el propósito del producto** (SC-001: "sin señales" ya no da 50). En implementación: medir el score real de las tres fixtures con el pipeline nuevo (incluido el aporte de banderas 003: un correo interno sin `Authentication-Results` puede sumar puntos y mantener la ruta media); si la ruta cambia, actualizar la metadata `_test` de la fixture con el motivo en el commit y **aprobación explícita del usuario** (Art. II.7). `malicious.json` se mantiene en ruta maliciosa con `b = -1.0` (D2: 80.5 % + puntos de banderas/URLs).

**Rationale**: la expectación vieja codifica el defecto que la spec corrige; no es "relajar una prueba para que pase" sino actualizar el contrato de la fixture al nuevo comportamiento especificado — pero exige aprobación explícita por ser una prueba existente.

## Incógnitas restantes (marcadas [VERIFICAR], no bloquean el plan)

1. **Valor calibrado del sesgo** — D2 fija -1.0 como default factible; la calibración por curva ROC con M13 queda pendiente (AC-SCO-04 es report-only).
2. **Peso original de entrenamiento y fecha** — el JSON documenta la fecha de congelamiento de v1 (2026-10-27) y `semilla: 42` (semilla del manifiesto de la spec 015); la fecha/semilla originales del entrenamiento GA son `[VERIFICAR]`.
3. **AC-SCO-04** — el conjunto y el harness viven en la rama paralela `test/conjunto-evaluacion` (spec 015), aún sin merge a `main`; la medición recall ≥ 95 % / FP ≤ 2 % se ejecuta cuando ambas ramas convivan (quickstart lo documenta). Report-only: si no se cumple, se informa el resultado sin ajustar umbrales.
4. **Aporte real de banderas 003 a los fixtures** — se mide en implementación (D10).
