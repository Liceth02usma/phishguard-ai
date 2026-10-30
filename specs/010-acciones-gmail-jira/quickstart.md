# Quickstart: Acciones Idempotentes en Gmail y Jira

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contract**: [contracts/acciones.md](./contracts/acciones.md)

Guía de validación ejecutable de la spec 010. Sin código de implementación.

## 1. Previos

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt     # sin dependencias nuevas

# .env — variables relevantes:
# ACCIONES_DRY_RUN=true              (por defecto; poner false en producción)
# JIRA_INSTANCE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN  (Jira; opcional en pruebas)
# MONGODB_ATLAS_CLUSTER_URI          (idempotencia; opcional, fallback in-memory)
```

## 2. Validación por escenarios

### V1 — DRY_RUN no ejecuta escrituras (AC-ACT-01)

```powershell
python -m pytest tests/unit/test_ac_act_01_dry_run.py -v
```

**Esperado**: passed — con `DRY_RUN=true`, ningún adapter de escritura es llamado; todas las acciones tienen `ejecutada=False` y `motivo="dry_run"`.

### V2 — Idempotencia por message_id (AC-ACT-02)

```powershell
python -m pytest tests/unit/test_ac_act_02_idempotencia.py -v
```

**Esperado**: passed — procesar el mismo `message_id` dos veces ejecuta acciones solo la primera; la segunda retorna `motivo="idempotencia"`.

### V3 — Nunca eliminar correos (AC-ACT-03)

```powershell
python -m pytest tests/unit/test_ac_act_03_no_eliminar.py -v
```

**Esperado**: passed — la tabla de mapeo no contiene acciones de eliminación; `GmailAdapter` no expone método `eliminar`; AST gate verifica ausencia de `trash`/`delete`/`eliminar`.

### V4 — Escapar y truncar texto del atacante (AC-ACT-04)

```powershell
python -m pytest tests/unit/test_ac_act_04_escapar_truncar.py -v
```

**Esperado**: passed — asunto con HTML, markup Jira y 10 000 caracteres se escapa y trunca correctamente.

### V5 — Auditoría de acciones (AC-ACT-05)

```powershell
python -m pytest tests/unit/test_ac_act_05_auditoria.py -v
```

**Esperado**: passed — cada acción produce un `ResultadoAccion` con `accion`, `destino`, `identificador`, `ejecutada`, `motivo`, `timestamp`.

### V6 — Tabla de acciones por veredicto (AC-ACT-06)

```powershell
python -m pytest tests/unit/test_ac_act_06_tabla_acciones.py -v
```

**Esperado**: passed — cada veredicto produce exactamente las acciones indicadas en FR-001.

### V7 — Deduplicación por campaña (AC-ACT-07)

```powershell
python -m pytest tests/unit/test_ac_act_07_campana.py -v
```

**Esperado**: passed — dos correos de la misma campaña (misma huella) crean un solo ticket; el segundo se vincula al primero.

### V8 — Resiliencia ante fallo de Jira (AC-ACT-08)

```powershell
python -m pytest tests/unit/test_ac_act_08_resiliencia_jira.py -v
```

**Esperado**: passed — si Jira falla, acciones de Gmail se ejecutan, error se registra, no hay bucle de reintento.

### V9 — Compuerta completa

```powershell
python scripts/verify.py
```

**Esperado**: exit 0.

## 3. `[VERIFICAR]` items

| ID | Item | Razón |
|---|---|---|
| V1 | Label "Revisar Seguridad" creada en Gmail | Requiere cuenta Gmail real |
| V2 | Custom field `huella_campaña` en Jira | Requiere configuración manual en Jira |
| V3 | Idempotencia con MongoDB real | Requiere `MONGODB_ATLAS_CLUSTER_URI` |
