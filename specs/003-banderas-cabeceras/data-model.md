# Data Model: Banderas Deterministas de Cabeceras y Remitente

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Investigación**: [research.md](./research.md)

Modelos de datos del paquete `src/level2_agent/banderas/`. Todo es Pydantic (Art. III.4)
salvo los objetos internos de evaluación, que son `dataclass(frozen=True)` como en
`normalizacion/limites.py` (solo memoria, no forman parte del contrato público).

## Catálogo 5.1 (fuente única de verdad)

Constante `CATALOGO_BANDERAS` en `modelos.py`: `dict[codigo, (severidad, puntos)]`,
transcripción literal de la sección 5.1 de `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`
(Art. VI.2: el código no admite puntos propios). Las banderas de esta spec son las 16
enumeradas en FR-005; `LIMITE_EXCEDIDO` pertenece a la spec 002 y no se duplica aquí.

| Código | Severidad | Puntos | Regla (resumen) |
|---|---|---|---|
| `SPF_FALLA` | media | 10 | SPF = fail o softfail |
| `DKIM_FALLA` | media | 10 | DKIM = fail |
| `DMARC_FALLA` | alta | 15 | DMARC = fail |
| `AUTH_NO_EVALUABLE` | baja | 5 | Sin `Authentication-Results` confiable |
| `REPLY_TO_DISTINTO` | media | 10 | Dominio de `Reply-To` ≠ dominio de `From` |
| `RETURN_PATH_DISTINTO` | baja | 5 | Dominio de `Return-Path` ≠ dominio de `From` |
| `NOMBRE_SUPLANTA` | alta | 15 | Nombre visible con marca/contacto interno en dominio externo |
| `DOMINIO_PARECIDO` | alta | 20 | Distancia ≤ 2 con dominio propio/marca, homoglifos o punycode |
| `DOMINIO_PUNYCODE` | media | 10 | El dominio contiene `xn--` |
| `MESSAGE_ID_DISTINTO` | baja | 5 | Dominio del `Message-ID` ≠ dominio del remitente (salvo proveedores de envío) |
| `RECEIVED_INCONSISTENTE` | media | 10 | Saltos `Received` fuera de orden o IP privada en el primer salto externo |
| `FECHA_ANOMALA` | baja | 5 | Fecha > 24 h en el futuro o > 1 año en el pasado |
| `REPLY_TO_GRATUITO` | media | 10 | `Reply-To` en dominio gratuito con `From` corporativo |
| `REMITENTE_EXTERNO_COMO_INTERNO` | alta | 15 | Contenido aparente interno desde dominio externo |
| `DOMINIO_NUEVO` | alta | 15 | Dominio registrado hace < 30 días (RDAP) |
| `DOMINIO_EDAD_DESCONOCIDA` | informativa | 0 | RDAP no respondió (sin penalización, FR-006) |

Constantes de umbral (Art. III.6): `TOPE_PUNTOS_BANDERAS = 60`,
`UMBRAL_DISTANCIA_EDICION = 2`, `DIAS_CACHE_RDAP = 7`, `TIMEOUT_RDAP_SEGUNDOS = 5`,
`DIAS_DOMINIO_NUEVO = 30`, `DIAS_FECHA_FUTURA = 1`, `ANIOS_FECHA_VIEJA = 1`,
`MAPA_HOMOGLIFOS`, `REDES_PRIVADAS` (redes del M04b vía `ipaddress`).

## Entidades públicas

### `BanderaActivada` (Pydantic)

| Campo | Tipo | Validación | Origen |
|---|---|---|---|
| `codigo` | `str` | debe ser clave de `CATALOGO_BANDERAS` | estrategia que la activa |
| `severidad` | `Literal["baja","media","alta","informativa"]` | copia del catálogo | catálogo (D12) |
| `puntos` | `int` | `ge=0`; copia del catálogo | catálogo |
| `detalle` | `str` | no vacío; describe dominios/evidencias, **sin** direcciones de correo completas (V.4) | estrategia |

Invariantes: sin dos entradas con el mismo `codigo` en un `ResultadoBanderas`;
`severidad`/`puntos` siempre coinciden con el catálogo (el motor los rellena desde la
constante: una estrategia solo aporta `codigo` + `detalle`).

### `EstadosAutenticacion` (Pydantic)

| Campo | Tipo | Valores admitidos |
|---|---|---|
| `spf` | `str` | `desconocido` (default), `pass`, `fail`, `softfail`, `neutral`, `none`, `permerror`, `temperror` |
| `dkim` | `str` | ídem |
| `dmarc` | `str` | ídem |

`desconocido` = no evaluado (cabecera ausente, no confiable o método ausente:
FR-002/AC-HDR-03). Es **información**, no bandera.

### `ResultadoBanderas` (Pydantic) — salida de `evaluar_banderas`

| Campo | Tipo | Validación |
|---|---|---|
| `banderas` | `list[BanderaActivada]` | orden estable = orden del catálogo 5.1; sin códigos repetidos |
| `estados_autenticacion` | `EstadosAutenticacion` | siempre presente (3 campos) |
| `puntos_totales` | `int` | `0 ≤ puntos_totales ≤ TOPE_PUNTOS_BANDERAS (60)`; `min(suma, 60)` (D8/AC-HDR-05) |

### `ConfigBanderas` (Pydantic) — inyectado o `desde_entorno()`

| Campo | Tipo | Env | Default |
|---|---|---|---|
| `authserv_id` | `str` | `AUTHSERV_ID` | `""` (conservador: nada de confianza → `AUTH_NO_EVALUABLE`, V.1) |
| `dominios_propios` | `frozenset[str]` | `DOMINIOS_PROPIOS` | vacío |
| `marcas_protegidas` | `frozenset[str]` | `MARCAS_PROTEGIDAS` | vacío |
| `contactos_internos` | `frozenset[str]` | `CONTACTOS_INTERNOS` | vacío |
| `terminos_internos` | `frozenset[str]` | `TERMINOS_INTERNOS` | vacío |
| `dominios_gratuitos` | `frozenset[str]` | `DOMINIOS_GRATUITOS` | gmail/hotmail/outlook/yahoo/live/icloud/proton.me/protonmail.com (D9, sustituible) |
| `proveedores_envio` | `frozenset[str]` | `PROVEEDORES_ENVIO` | vacío |

Validación: dominios normalizados a minúsculas y sin punto final; entrada con formato
inválido (espacios en listas, dominio con esquema o `/`) → `ConfiguracionError` al
construir (fail-fast, III.9).

## Objetos internos (dataclass frozen, no contrato)

### `ContextoEvaluacion`

Transporta lo que toda estrategia necesita: `correo: EmailData`, `config:
ConfigBanderas`, `ahora: datetime` (UTC, inyectado: D13), `estados:
EstadosAutenticacion` (calculados una vez por autenticación) y `consultar_edad:
Callable[[str], EdadDominio]` (puente al RDAP ya memoizado).

### `EdadDominio`

`fecha_registro: datetime | None` (`None` = desconocida/falla). El motor lo convierte:
`< 30 días` → `DOMINIO_NUEVO`; `None` → `DOMINIO_EDAD_DESCONOCIDA`.

### `EntradaCacheRDAP` y ciclo de vida

```
miss ──consulta OK──▶ hit (expira = ahora + 7 días) ──TTL vencido──▶ miss (se reconsulta)
   └──cualquier fallo──▶ memoizado solo DENTRO de la misma invocación (sin entrada persistente)
```

No hay máquina de estados en el dominio: `evaluar_banderas` es una función pura
correo + config + ahora → resultado; la única estado mutante es la caché de RDAP del
proceso (D7).

## Protocolo `ClienteRDAP`

```python
class ClienteRDAP(Protocol):
    def registrar_evento(self, dominio: str) -> datetime | None:
        """Fecha de registro o None si no se pudo determinar (nunca lanza)."""
```

Implementación real `RequestsRDAP` (requests, timeout 5 s, `https://rdap.org/domain/`,
dominio saneado por regex); en pruebas se inyecta un doble. Nota: `registrar_evento`
nunca propaga excepciones (AC-HDR-06); los fallos devuelven `None`.

## Relaciones

```
evaluar_banderas(correo, config, ahora, cliente_rdap)
  └─ motor.py: registry ordenado de estrategias
       ├─ autenticacion.py ──▶ BanderaActivada (4 códigos) + EstadosAutenticacion
       ├─ identidad.py     ──▶ BanderaActivada (5 códigos)
       ├─ dominios.py      ──▶ BanderaActivada (2 códigos)  [tldextract + distancia]
       ├─ contexto.py      ──▶ BanderaActivada (3 códigos)
       └─ rdap.py          ──▶ BanderaActivada (2 códigos)  [ClienteRDAP + caché]
  └─ motor aplica tope 60 ──▶ ResultadoBanderas
```

`EmailData` (spec 002) es la única entrada de dominio: de `cabeceras` se leen
`Authentication-Results`, `From`, `Reply-To`, `Return-Path`, `Message-ID`, `Date`,
`Received`; de los campos ya normalizados, `subject` y `texto_limpio`.

## Validaciones cruzadas (tests del modelo)

1. Toda bandera activada pertenece al catálogo y sus `puntos`/`severidad` coinciden.
2. `puntos_totales == min(sum(b.puntos), 60)` para cualquier combinación (propiedad
   con `hypothesis`: generado un subconjunto de códigos).
3. Sin códigos repetidos; orden estable igual al orden del catálogo.
4. `detalle` sin `@` de dirección completa (regex de prueba sobre todos los detalles
   producidos por los fixtures).
