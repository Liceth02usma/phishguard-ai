# Quickstart: validación de la spec 004 (análisis y expansión de URLs)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contrato**: [contracts/analizar-urls.md](./contracts/analizar-urls.md)

Guía de **ejecución y verificación**. No contiene implementación: los cuerpos de
funciones y tests viven en `src/level2_agent/analisis_urls/` y `tests/unit/`
(según `tasks.md`, fase TDD).

## 0. Prerrequisitos

```powershell
# venv (si no existe) + dependencias — Windows, según AGENTS.md
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- **Sin red externa**: todas las pruebas usan dobles DNS/HTTP y un servidor local de
  loopback (Art. II.5). No se necesita `.env` ni claves para esta spec.
- Rama de trabajo: `feature/analisis-urls` (checkout en T00 — ver Constitución I.1
  en [plan.md](./plan.md)).

## 1. Escenarios de validación

### E1 — Pruebas de los criterios de aceptación (rápida)

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ -k "ac_url" -v
```

**Esperado**: 7 archivos `test_ac_url_01..07` en verde, cada uno con
`@pytest.mark.ac("AC-URL-NN")` declarado (trazabilidad 100 %: 7/7 AC).
Cobertura mínima sobre `src/level2_agent/analisis_urls/`: **≥ 80 % líneas y ramas**
(Art. II.3).

### E2 — Trazabilidad AC → prueba

```powershell
.venv\Scripts\python.exe scripts\check_trazabilidad_ac.py --spec specs/004-analisis-urls/spec.md
```

**Esperado**: salida indicando que cada `AC-URL-01..07` del spec tiene al menos una
prueba asociada; exit 0.

### E3 — Unidad: catálogo, expansión, SSRF y saneador

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_banderas_url.py `
  tests\unit\test_expansion.py tests\unit\test_ssrf.py tests\unit\test_sanitizacion.py -v
```

**Esperado**:
- `test_banderas_url.py`: los 13 códigos de la tabla de `data-model.md` con par
  positivo/negativo; `puntos`/`severidad` = catálogo 5.2 literal (I5).
- `test_expansion.py`: máquina de estados de `data-model.md` recorrida por tabla de
  decisión — 4 saltos ⇒ `expandida`; 5.º salto pendiente ⇒ `limite_saltos` +
  `REDIRECCION_EXCESIVA`; nunca existe una 6.ª petición (I7, D9).
- `test_ssrf.py`: cada red de FR-004 (IPv4 e IPv6) ⇒ `bloqueada_ssrf`; red pública ⇒
  permitida (I1).
- `test_sanitizacion.py`: propiedades `hypothesis` — ningún valor con forma de correo
  ni `token`/`password` sobrevive al saneador (I3, AC-URL-06).

### E4 — Servidor local: SSRF y ausencia de cuerpos (AC-URL-02/04)

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_ac_url_02_ssrf_privados.py `
  tests\unit\test_ac_url_04_sin_cuerpo.py -v
```

**Esperado**: servidor de loopback arrancado como context manager
(`tests/unit/dobles_red.py`); cuando el DNS de prueba resuelve a privada/loopback,
el servidor recibe **cero** peticiones (I1); en las peticiones permitidas, el
servidor registra **cero lecturas de cuerpo** y `RespuestaRedireccion.ya_leido`
queda en `False` (I2). Cierre limpio del servidor en todos los caminos.

### E5 — Puerta completa (compuertas de la constitución)

```powershell
.venv\Scripts\python.exe scripts\verify.py
```

**Esperado**: exit 0 e informe en consola (Art. IV.1), con:
- ruff y `mypy --strict` sin advertencias sobre `src/level2_agent/analisis_urls/`;
- cobertura de `scripts/` + `normalizacion/` + `models/` + **`analisis_urls/`**
  (ampliación en `scripts/verify.py`, research D14) ≥ umbral efectivo;
- `pip-audit` y `gitleaks` en verde;
- regresión `tests/test_pipeline.py` PASS (E6).

### E6 — Regresión del pipeline actual (D11: sin wiring)

```powershell
.venv\Scripts\python.exe tests\test_pipeline.py
```

**Esperado**: PASS en todos los fixtures — la spec 004 no altera `agent.py`,
`prompts.py`, el poller ni `normalizacion/`; `EmailData.urls` se sigue poblando con
`extraer_urls` de la 002 (D2).

### E7 — Demostración manual (offline)

```powershell
.venv\Scripts\python.exe -c @"
from src.level2_agent.models import EmailData
from src.level2_agent.analisis_urls import analizar_urls
correo = EmailData(subject='hola', from_='a@b.com', to='c@d.com',
                   textBody='http://evil.example/ paga aqui', htmlBody='', headers='{}')
r = analizar_urls(correo)   # sin acortadores → 0 E/S de red
print(len(r.urls), [b.codigo for b in r.banderas])
"@
```

**Esperado**: imprime `1 [...]` con al menos `URL_HTTP_SIN_CIFRADO`;
**cero** peticiones de red (sin acortadores en la URL, `estado = no_acortadora`).
Con `deps` inyectados (doble DNS/HTTP) se demuestra la expansión sin salir de
loopback.

## 2. Puntos `[VERIFICAR]` (Art. VI.3)

| # | Pendiente | Dónde se decide |
|---|---|---|
| V1 | Umbral de `URL_SUBDOMINIOS_EXCESIVOS` (propuesta: 4 etiquetas) | `research.md` D8 — ajustable por `URL_SUBDOMINIOS_MAX` |
| V2 | Lista por defecto de `TLD_RIESGO` (propuesta en D8) | `research.md` D8 |
| V3 | Lista por defecto de `PARAMETROS_TRACKING` (propuesta en D8) | `research.md` D8 |
| V4 | Comportamiento real de los acortadores (las pruebas usan cadenas locales; nada toca la red real) | validar en demo con red si el usuario lo aprueba |
| V5 | Pinning de IP completo en la ventana TOCTOU del cliente HTTP | `research.md` D7 — requerido solo si 006/008 lo exige |
| V6 | Tope global de 60 puntos por correo cuando se concatenern 003+004 | `research.md` D3 — lo unifica 007 |
| V7 | Peor caso de 200 acortadores (expansión secuencial × 5 s) | `research.md` D13 — solo si la demo lo exhibe |

## 3. Criterios de terminado (Definition of Done)

- [ ] E1–E6 en verde con `scripts/verify.py` exit 0.
- [ ] 7/7 AC con prueba marcada (`@pytest.mark.ac`) y E2 exit 0.
- [ ] `models.py`, `agent.py`, `prompts.py`, poller y `normalizacion/` sin diff (D11/D2).
- [ ] Cero dependencias nuevas en `requirements.txt`.
- [ ] `[VERIFICAR]` V1–V7 listados en el informe final.
