# Contrato: API pública del paquete `banderas`

**Spec**: [spec.md](./spec.md) | **Modelo de datos**: [../data-model.md](../data-model.md)

Contrato de la librería que entregará la spec 003. Es el interfaz que consumirán la
spec 007 (scoring), la spec 008 (motor de decisión) y, con la misma forma de JSON, la
spec 12 (API REST, sección 14.x del plan). Formato: Python + Pydantic (librería
interna; sin endpoints).

## API pública (`src.level2_agent.banderas`)

```python
def evaluar_banderas(
    correo: EmailData,
    config: ConfigBanderas | None = None,
    ahora: datetime | None = None,
    cliente_rdap: ClienteRDAP | None = None,
) -> ResultadoBanderas: ...
```

| Parámetro | Tipo | Default | Semántica |
|---|---|---|---|
| `correo` | `EmailData` | — | Correo normalizado (spec 002); fuente única de cabeceras y campos |
| `config` | `ConfigBanderas \| None` | `ConfigBanderas.desde_entorno()` | authserv-id y listas configurables (research D9) |
| `ahora` | `datetime \| None` | `datetime.now(timezone.utc)` | Reloj inyectado para `FECHA_ANOMALA` y la caché RDAP (D13); las pruebas lo fijan |
| `cliente_rdap` | `ClienteRDAP \| None` | `RequestsRDAP()` | Adapter de antigüedad de dominio (D7); las pruebas inyectan un doble |

También se exportan: `ConfigBanderas` (y su `ConfiguracionError`), `ResultadoBanderas`,
`BanderaActivada`, `EstadosAutenticacion`, `CATALOGO_BANDERAS`, `TOPE_PUNTOS_BANDERAS`
y el protocolo `ClienteRDAP`.

## Garantías

1. **Determinismo**: mismo `(correo, config, ahora, cliente_rdap)` → mismo resultado,
   con orden de `banderas` estable (orden del catálogo 5.1).
2. **Sin excepciones por red**: `evaluar_banderas` **nunca** lanza por fallas de RDAP
   (AC-HDR-06): cualquier caída, respuesta inválida o dominio mal formado produce
   `DOMINIO_EDAD_DESCONOCIDA` (informativa, 0 pts). Lo mismo aplica a `ClienteRDAP`:
   `registrar_evento` devuelve `None`, no lanza.
3. **Techo de puntos**: `0 ≤ puntos_totales ≤ 60` siempre; el tope recorta la suma
   publicada, no la lista de evidencias (AC-HDR-05).
4. **Autenticación de confianza única**: solo el `authserv-id` configurado puede
   fijar SPF/DKIM/DMARC; sin cabecera confiable los tres valen `desconocido` y se
   activa `AUTH_NO_EVALUABLE` (AC-HDR-02/03). `pass` jamás se infiere.
5. **Sin red en pruebas**: con `tldextract` empaquetado (`suffix_list_urls=()`) y un
   doble de `ClienteRDAP`, la evaluación completa es en memoria (Art. II.5).
6. **Sin PII en `detalle`**: los detalles describen dominios y evidencias, nunca
   direcciones de correo completas (Art. V.4).
7. **Sin IA**: ninguna bandera usa modelo de lenguaje (objetivo de la spec).

## Errores

| Condición | Comportamiento |
|---|---|
| Env con formato inválido al construir `ConfigBanderas` | `ConfiguracionError` (fail-fast, al inicio, no durante la evaluación) |
| Cualquier fallo de RDAP o dominio inválido | `DOMINIO_EDAD_DESCONOCIDA`, sin excepción |
| `EmailData` sin cabeceras relevantes | resultado con banderas posibles sin esas señales; `AUTH_NO_EVALUABLE` activa (no hay AR confiable) |

## Forma JSON de salida (anticipación del contrato de la spec 12)

Espejo de la sección 14.x de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`:
`{"codigo", "severidad", "puntos", "detalle"}` por bandera.

```json
{
  "banderas": [
    { "codigo": "DOMINIO_PARECIDO", "severidad": "alta", "puntos": 20,
      "detalle": "dominio paypa1.com a distancia 1 de la marca protegida paypal.com" },
    { "codigo": "AUTH_NO_EVALUABLE", "severidad": "baja", "puntos": 5,
      "detalle": "sin Authentication-Results del authserv-id configurado" }
  ],
  "estados_autenticacion": { "spf": "desconocido", "dkim": "desconocido", "dmarc": "desconocido" },
  "puntos_totales": 25
}
```

## Catálogo de códigos (los 16 de FR-005)

Ver la tabla completa con severidades y puntos en
[data-model.md](../data-model.md#catálogo-51-fuente-única-de-verdad): es la
transcripción del catálogo 5.1 y la única fuente de verdad del código.

## Fuera de alcance de este contrato

- Veredicto, score compuesto o `revision_manual` (specs 007/008).
- Persistencia del resultado (spec 11/12).
- Análisis de URLs, adjuntos o VirusTotal (specs 004–006).
- `LIMITE_EXCEDIDO` (spec 002, normalización).

## Consumidores previstos

| Spec | Uso |
|---|---|
| 007 (scoring genético) | banderas y `puntos_totales` como genes/penalizaciones deterministas |
| 008 (motor de decisión) | banderas como evidencia del veredicto |
| 12 (API REST) | `ResultadoBanderas` serializado en la respuesta de análisis |
