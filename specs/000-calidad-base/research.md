# Research: Compuertas de Calidad Automáticas

**Spec**: [spec.md](spec.md) | **Date**: 2026-10-22

## Decisiones de diseño (resuelven los "por ejemplo" de la spec)

### D1 — Comando único: `python scripts/verify.py` (+ wrapper `make verify`)

**Decision**: el comando único es `python scripts/verify.py`, cross-platform (Windows y Linux). Adicionalmente un `Makefile` con target `verify` para entornos Unix con `make` disponible.

**Rationale**: el repo es Windows-primary (README usa `.venv\Scripts\`) pero la constitución exige cross-platform. `make` no está garantizado en Windows. Un script Python es invocable igual en ambos SO y es él mismo auditable por las compuertas (ruff/mypy/pruebas).

**Alternativas consideradas**:
- `make verify` únicamente: rechazado por no estar garantizado en Windows.
- `just verify` (justfile): rechazado por añadir una dependencia extra.
- Script PowerShell `verify.ps1`: rechazado por no ser cross-platform.

### D2 — Marker `ac("AC-XXX-NN")`: plugin de pytest + opción `--ac-report`

**Decision**: registrar el marker `ac` en `pyproject.toml` (`[tool.pytest.ini_options] markers = ["ac(id): ..."]`). Un plugin/conftest recolecta las asociaciones prueba→AC. `scripts/check_trazabilidad_ac.py` parsea la spec, extrae los IDs `AC-CAL-NN` y los compara con los marcados; emite la lista de AC sin prueba (AC-CAL-05).

**Rationale**: integra con el ecosistema pytest sin reinventar trazabilidad. El marker es el mecanismo que exige el Art. II.6.

**Alternativas consideradas**:
- Docstrings con tags `# AC-CAL-01`: rechazado por no ser parseable estándar ni visible en `pytest --markers`.
- Base de datos externa de trazabilidad: rechazado por YAGNI.

### D3 — Cobertura: `pytest --cov --cov-branch --cov-fail-under=80`

**Decision**: configurar en `pyproject.toml` los flags de cobertura de líneas y ramas con umbral 80 % (Art. II.3). `verify.py` invoca pytest con estos flags. AC-CAL-03 se prueba con un módulo sintético que baja la cobertura por debajo de 80 % y verifica que `verify.py` falla.

**Rationale**: exige la constitución literalmente. El umbral 80 es constante `COBERTURA_MIN` en `_comunes.py`.

**Alternativas consideradas**: umbral 100 %: rechazado (la constitución exige 80 % global; 100 % solo era para "motor de decisión", requisito eliminado en v2.0.0).

### D4 — Detección de secretos: `gitleaks` vía pre-commit + step de CI

**Decision**: `gitleaks` corre como hook de pre-commit y como step del workflow `.github/workflows/verify.yml`. AC-CAL-04 se prueba con un archivo temporal que contiene una cadena con forma de API key (en un tmp dir, no en el repo) y verifica que gitleaks la detecta.

**Rationale**: `gitleaks` escanea repo e historial (AC-SEC-01 en spec 14 lo refuerza). pre-commit atrapa antes del commit; CI atrapa antes del merge.

**Alternativas consideradas**: `detect-secrets` (Yelp): válido pero `gitleaks` es el nombrado en la constitución y la spec.

### D5 — Longitud de archivos: script propio `check_longitud_archivos.py`

**Decision**: script que recorre `src/` y `tests/` contando líneas de `.py` y falla si alguno > 500, listando infractores. AC-CAL-01 se prueba generando en un tmp dir un archivo de 500 y uno de 501 líneas y verificando pasa/falla.

**Rationale**: `ruff` no tiene una regla de longitud de archivo por defecto. Un script propio es simple, testeable y ≤500 líneas.

**Alternativas consideradas**: regla custom de ruff: no existe nativa.

### D6 — Nombre de rama: script propio `check_nombre_rama.py`

**Decision**: script que lee la rama actual (`git branch --show-current`), exime `main` y `develop`, y valida el regex `^(feature|fix|refactor|chore|test|docs)/[a-z0-9]+(-[a-z0-9]+)*$`. AC-CAL-02 se prueba con una tabla de decisión de nombres válidos e inválidos sin tocar el repo (función pura que recibe el nombre).

**Rationale**: la validación es una función pura sobre un string; fácil de probar sin mocks de git. El comando git solo se invoca en el orquestador.

### D7 — CI: GitHub Actions

**Decision**: `.github/workflows/verify.yml` ejecuta `python scripts/verify.py` en cada pull request (AC-CAL-06). Bloquea el merge si falla (branch protection asumida).

**Rationale**: el repo ya está en GitHub (`remotes/origin`). GitHub Actions es nativo.

## Dependencias externas y dobles

- `gitleaks`: binario externo. En pruebas se invoca con un path configurable; si no está disponible, la prueba se salta con `pytest.skip` (no `xfail`) explicando que requiere instalación — esto no relaja una prueba de la spec (la spec prueba la lógica de detección, no la presencia del binario).
- `pip-audit`: invoca contra el entorno; en pruebas se usa un requirements fixture con una vulnerabilidad conocida para verificar que falla.
- `git`: invocado solo para leer el nombre de rama; testeado vía función pura.

## Sin NEEDS CLARIFICATION pendientes

Todas las decisiones se tomaron con la spec, la constitución y el plan de modificaciones. No hay valores inventados: los umbrales (80, 500) y el regex vienen de la constitución; las herramientas (`pytest`, `ruff`, `mypy`, `pip-audit`, `gitleaks`, `pre-commit`) vienen del hint de plan de la spec.
