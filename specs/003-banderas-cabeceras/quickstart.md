# Quickstart: Banderas Deterministas de Cabeceras y Remitente

**Spec**: [spec.md](./spec.md) | **Contrato**: [contracts/banderas-api.md](./contracts/banderas-api.md)

Guía de validación de la spec 003. Todos los pasos corren **sin red y sin claves de
servicios** (esta spec no usa Gemini, MongoDB ni Gmail): solo requiere el entorno
virtual del proyecto.

## Prerrequisitos

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt   # incluye tldextract con versión fija (nueva dependencia)
```

No hace falta `.env` para las pruebas: los fixtures construyen `ConfigBanderas` con
valores explícitos. Para usar el paquete contra correo real, definir en `.env`
(creado a partir de `.env.example`): `AUTHSERV_ID` (authserv-id de la pasarela propia)
y las listas configurables (`DOMINIOS_PROPIOS`, `MARCAS_PROTEGIDAS`, ...).

## 1. Pruebas unitarias (todas las AC)

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ -q
```

**Esperado**: todos verdes, cero fallos, cero `skip`/`xfail` nuevos. Incluye las
marcas `@pytest.mark.ac("AC-HDR-01..06")` y las pruebas unitarias del parser RFC 8601,
de dominios y del adapter RDAP.

## 2. Trazabilidad AC → pruebas

```powershell
.venv\Scripts\python.exe scripts\check_trazabilidad_ac.py --spec specs/003-banderas-cabeceras/spec.md
```

**Esperado**: exit 0 (cada AC-HDR-NN del spec tiene al menos una prueba marcada).

## 3. Cobertura del paquete nuevo

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ --cov=src/level2_agent/banderas --cov-branch --cov-fail-under=80
```

**Esperado**: ≥ 80 % de líneas **y** ramas sobre `src/level2_agent/banderas/`
(Art. II.3).

## 4. Compuerta completa del repositorio

```powershell
.venv\Scripts\python.exe scripts\verify.py
```

**Esperado**: exit 0 (ruff, `mypy --strict`, pruebas con cobertura, longitud de
archivos, nombre de rama y compuertas ya existentes, sin bajar umbrales).

## 5. Demostración manual del comportamiento (positivo y negativo)

Construir dos `EmailData` en memoria (uno con cabeceras "de confianza" y marca
suplantada, otro idéntico pero sin `Authentication-Results` propio) y llamar
`evaluar_banderas` con `ConfigBanderas(authserv_id="mail.empresa.com",
marcas_protegidas=frozenset({"paypal.com"}))` y `ahora` fijo. Verificación esperada
(detalle en [data-model.md](../data-model.md)):

| Escenario | Esperado |
|---|---|
| `From: paypa1.com` + AR del authserv-id propio con `spf=pass dkim=pass dmarc=pass` | activa `DOMINIO_PARECIDO`; **no** activa banderas de autenticación; estados en `pass` |
| Mismo correo sin cabecera del authserv-id propio (o con la de un servidor externo) | `AUTH_NO_EVALUABLE` + tres estados `desconocido` (AC-HDR-02/03) |
| `From: empresa.com` vs marca `empresa.com` en `empresa.com.co` | **no** activa `DOMINIO_PARECIDO` (distancia 3, subcadena prohibida) |
| Combinación de banderas que sumarían 61 puntos | `puntos_totales == 60` (AC-HDR-05) |

Un atajo cómodo sin escribir archivos: una celda de Python (o `python -c`) que
construya `EmailData(cabeceras=[Cabecera(nombre=..., valor=...), ...])` y imprima
`resultado.model_dump()`.

## 6. (Opcional, con red) RDAP real — fuera de CI

Paso **manual**, solo para el `[VERIFICAR]` de `research.md`: consultar
`https://rdap.org/domain/<dominio-real>` y comparar el `eventDate` de `registration`
con lo que devuelve `RequestsRDAP`. Las caídas o respuestas distintas a la esperada se
reportan como hallazgo (research D7), nunca rompen las pruebas (que usan dobles).

## Mapeo de escenarios → criterios de aceptación

| Escenario quickstart | Criterio |
|---|---|
| Par positivo/negativo por bandera (paso 5 + fixtures de tests) | AC-HDR-01 / SC-001 |
| AR de servidor externo ignorado | AC-HDR-02 |
| Sin AR confiable → desconocido + `AUTH_NO_EVALUABLE` | AC-HDR-03 |
| `paypa1.com` sí / `empresa.com.co` no | AC-HDR-04 |
| Suma 61 → 60 | AC-HDR-05 / SC-002 |
| RDAP caído sin excepción y sin puntos | AC-HDR-06 / SC-003 |

## `[VERIFICAR]` (Art. VI.3)

1. Valor real de `AUTHSERV_ID` de la pasarela propia (definirlo en `.env`).
2. Formato real de la respuesta RDAP del servicio (paso 6).
3. Cabeceras reales de Gmail al poller (`token.json` ausente en este entorno).
