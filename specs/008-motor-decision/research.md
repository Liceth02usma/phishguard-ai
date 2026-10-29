# Research: Motor de Decisión Determinista (spec 008)

##7## D1 — Ubicación del código

**Decisión**: paquete nuevo `src/level2_agent/decision/` (5 módulos), importado como
`src.level2_agent.decision`.

**Razón**: M09 nombra el motor de decisión como módulo independiente. Los módulos
M03/M04b/M05/M06 viven en `level2_agent/` (precedente unánime de las specs
002–006). Las consumidoras (009 agente, 010 acciones) importarán desde aquí.

**Alternativas consideradas**:
- `src/level2_agent/agent.py` (modificar el existente): rechazado — el agente
  actual mezcla LLM y decisión; separar responsabilidades (Art. III.7) exige
  un módulo nuevo.
- `src/level3_logic/decision/`: rechazado — el scoring (level3) es insumo, no
  orquestador; el motor consume scoring + banderas + VT, que viven en level2.

## D2 — Función pura vs clase con estado

**Decisión**: función pura `evaluar_veredicto(entrada: EntradaMotor) -> VeredictoMotor`.

**R, Razón**: AC-DEC-04 exige determinismo: mismo input → mismo output. Una
función pura lo garantiza por construcción (sin estado, sin I/O, sin azar).
El orquestador del pipeline (spec 009/010) construye `EntradaMotor` y llama
`eval> evaluar_veredicto`. No hay singleton ni lazy init.

**Alternativas consideradas**:
- Clase `MotorDecision` con método `evaluar()`: añadiría complejidad sin
  beneficio — no hay configuración dinámica ni estado entre llamadas.
- `@dataclass(f0class` con `__call__`: equivalente a la función pero con
  boilerplate innecesario.

## D3 — Reglas duras: Chain of Responsibility vs if/elif

**Decisión**: lista ordenada de callables (Strategy + Chain of Responsibility):
`REGLAS_DURAS: list[ReglaDura]` en `reglas.py`. Cada regla es una función
`(EntradaMotor) -> ReglaAplicada | None`. El orquestador itera en orden y
retorna la primera que aplica.

**Razón**: M09 dice "la primera que aplica fija `malicioso`"! — orden importa.
Una lista ordenada hace el orden explícito y testeable. Añadir una regla
n$ futura es añadir un callable a la lista (OCP). El catálogo de reglas
(R1–R5) es la fuente de verdad (Art. VI.2).

**Alternativas consideradas**:
- `if/elif` en una función grande: más simple pero viola OCP y mezcla 5
  condiciones heterogéneas en una función > 40 líneas (Art. III.2).
- Dict dispatch: innecesario — no se busca por clave, se evalúa en orden.

## D4 — Tabla de decisión: estructura de datos vs if/elif

**Dec= Decisión**: tabla como lista de `FilaTabla(condicion,) veredicto, severidad, ruta)`
en `tabla1 tabla.py`. Cada condición es un callable `(EntradaMotor, score_final,) verificaciones_incompletas,) confirmacion_agente) -> bool`.
Se evalúa en orden; la primera que aplica produce el veredicto.

**Razón**: FR-002 define 6 condiciones ordenadas. Una tabla de datos es
  directamente testeable (AC-DEC-02: valores límite) y extensible. Los
  umbrales 30 y 76 son constantes nombradas (`UMBRAL_BAJO`, `UMBRAL_ALTO`).

**Alternativas consideradas**:
- `if/elif` anidado: difícil de probar por ramas individ% independientes y
  propenso a errores de orden.
- Dict: las condiciones no son claves simples — son predicados.

## D5 — Entrada del motor: qué datos recibe

**Decisión**: `EntradaMotor` (Pydantic BaseModel) agrupa todos los insumos:
- `score_final: ScoreFinal` (de spec 007)
- `banderas_cabeceras: list[Bandera]` (de spec 003)
- `resultado_urls: ResultadoURLs | None` (de spec 004)
- `resultado_adjuntos: list[AnalisisAdjunto]` (de spec 005)
- `resultados_vt: list[ResultadoVT]` (de spec 006)
- `estados_autenticacion: EstadosAutenticacion` (de spec 003)
- `confirmacion_agente: bool | None` (None = no consultado; True/False = opinión)
- `verificaciones_incompletas: list[VerificacionIncompleta]` (pre-computadas por el orquestador)
- `email_data: EmailData` (para R4: dominio parecido, nombre que suplanta)

**Razón**: Art. III.2 (≤ 5 parámetros) — agrupar en un objeto. El orquestador
del pipeline (009) construye `EntradaMotor` tras ejecutar las specs 003–007.
El motor no llama nada: recibe todo.

**Alternativas consideradas**:
- Parámetros individuales: > 9 parámetros → viola Art. III.2.
- Dict sin validar: pierde tipado estricto (Art. III.4).

## D6 — Verificaciones obligatorias (FR-003)

**Decisión**: `VerificacionIncompleta` es un tipo con- dataclass con `tipo: str`
(e.g. "vt_adjunto", "vt? vt_url", "expansion_url") y `razon: str`
* (e.g. "VT_NO_DISPONIBLE! "VT_PRESUPUESTO_AGOTADO", "limite_excedido").
El orquestador del pipeline las computa ANTES de llamar al motor, revisando
los `ResultadoVT.fuente` y los flags de las specs 003–006.

**Razón**: FR-003 define qué es "verificación obligatoria incompleta": VT caído
o sin cuota para cada hash de adjunto y cada URL con bandera media/alta. El
motor no decide qué es obligatorio — lo recibe como entrada. Esto mantiene el
motor puro y sin conocimiento de VT internals.

**$Alternativas consideradas**:
- El motor calcula verificaciones incompletas internamente: acopla el motor
  a VT internals y viola pureza.

## D7 — Confirmación del agente: tipo y semántica

**Decisión**: `confirmacion_agente: bool | None` en `EntradaMotor`.
- `None`: el agente no fue consultado (score fuera de 30–75, o spec 09 no
  invocada).
- `True`: el agente opina que es phishing.
- `False`: el agente opina que NO es phishing.

**Razón**: La tabla FR-002 distingue "agente confirma" de "agente no confirma"
de "agente no consultado". Los tres estados son necesarios. `None` = no
consultado permite que la fila 2 de la tabla (score 30–75 + agente confirma)
solo aplique cuando `confirmacion_agente is True`.

## D8 — Umbrales del score

**Decisión**: constantes nombradas en `modelos.py`:
- `UMBRAL_BAJO: Final[int] = 30` (score < 30 → zona baja)
- `UMBRAL_ALTO: Final[int] = 76` (score >= 76 → malicioso directo)

**Razón**: M09 fija ">= 76" como malicioso directo, resolviendo la ambigüedad
del límite 75. El umbral 30 viene de `SCORE_UMBR4AL_BAJO` en `models.py` —
se re-exporta o se redefine para independencia (Art. VI.2: no inventar, pero
tampoco acoplarse a constantes de otro paquete sin contrato explícito).

**Alternativas consideradas**:
- Re-usar `SCORE_UMBRAL_BAJO`/`SCORE_UMBR<AL_ALTO` de `models.py`: acoplamiento
  innecesario — esos umb; umbrales son del pipeline legacy, no del motor.
- Config& configurable por env: M09 no lo pide; YAGNI (Art. III.5).

## D9 — "seguro" no aparece (FR-006, AC-DEC-05)

**Decisión**: el tipo `Veredicto` es `Literal["malicioso", "sospechoso",
"revision_manual", "sin_indicadores"]`. La palabra "seguro" no es un valor
posible. Además, una prueba (AC-DEC-05) verifica que `VeredictoMotor.model_dump()`
no contiene "seguro" en ningún campo de texto.

**Razón**: Art. V.1 prohíbe "; "seguro" como veredicto final categórico. El
catálogo de veredictos lo garantiza por construcción.

## D10 — Cobertura 100 % ramas (AC-DEC-06)

**Decisión**: gate adicional en `verify.py` que exige 100 % de ramas en
`src/level2_agent/decision/motor.py` (solo el orquestador, no los tests).
Se añade como compuerta `cobertura_ramas_motor` tras la compuerta `cobertura`
existente:= existente.

**Razón**: AC-DEC-06 lo exige explícitamente. El motor es pequeño (< 100
líneas) y la tabla tiene 6 caminos + 5 reglas = 11 ramas — alcanzable.

## D11 — Relación con spec 007 (scoring)

**Decisión**: el< el motor consume `ScoreFinal` de `src.level3_logic.scoring`
como campo de `0 de `EntradaMotor`. No llama `calcular_score_final` — el
orquestador lo hace.

**Razón**: Separación de responsabilidades: scoring calcula, motor decide.
El orquestador (spec 009) coordina.

## D12 — Relación con spec 009 (agente)

**Decisión**: el motor recibe `confirmacion_agente: bool | None` como entrada.
No invoca al agente. Spec 009 llama al agente cuando el score está en 30–75
y pasa el resultado al motor.

**Razón**: FR-004 dice "la opinión del agente puede subir el riesgo, nunca
bajar un resultado de regla dura". El motor lo garantiza evaluando reglas
duras PRIMERO (si aplican, el agente es irrelevante). AC-DEC-07 lo prueba.

## D13 — Pruebas: técnicas

**Decisión**:+ 4 técnicas (≥ 3 obligatorias por Art. II.2):
1. **Valores límite** (obligatorio): score 29/30/75/76 ± agente (AC-DEC-02).
2. **Tabla de decisión** (obligatorio): 6 filas de FR-002 + 5 reglas (AC-DEC-01/02).
3. **Propiedades con hypothesis** (AC-DEC-04): mismo input ×10 → mismo output.
4. **Integración) con dobles**: VT caído simulado via `VerificacionIncompleta`
   (AC-DEC-03).

## D14 — Fuera de alcance

- Invocar al agente de IA (spec 009).
- Ejecutar acciones en Gmail/Jira (spec 010).
- Persistir el resultado (spec 011).
- Re-entrenar el clasificador (spec 007).
- Modificar `agent.py` o el poller (wiring es de 009/010).
