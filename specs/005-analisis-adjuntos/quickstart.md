# Quickstart: Análisis Estático de Adjuntos

**Spec**: [spec.md](./spec.md) | **Contrato**: [contracts/adjuntos-api.md](./contracts/adjuntos-api.md)

Guía de validación de la spec 005. Todos los pasos corren **sin red y sin claves de
servicios** (esta spec no usa Gemini, MongoDB, Gmail ni VirusTotal): solo requiere el
entorno virtual del proyecto. Los archivos maliciosos de prueba (EICAR, zip bomb,
ejecutable renombrado) **se generan en memoria** en las pruebas (SC-003): no hay
nada peligroso que descargar ni guardar.

## Prerrequisitos

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt   # incluye filetype==1.2.0, oletools==0.60.2, pypdf==6.21.2 (nuevas deps fijadas)
```

No hace falta `.env` para las pruebas: los fixtures construyen `ConfigAdjuntos` con
defaults. Para cambiar listas o límites en uso real, definir en `.env` (creado a
partir de `.env.example`): `ADJ_EXTENSIONES_RIESGO`, `ADJ_EXTENSIONES_HTML`,
`ADJ_EXTENSIONES_DOCUMENTO`, `ADJ_LIMITE_ENTRADAS_ZIP`,
`ADJ_LIMITE_DESCOMPRIMIDO_ZIP`, `ADJ_RATIO_MAXIMO_ZIP`.

## 1. Pruebas unitarias (todas las AC)

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ -q
```

**Esperado**: todos verdes, cero fallos, cero `skip`/`xfail` nuevos. Incluye las
marcas `@pytest.mark.ac("AC-ADJ-01..06")` y las pruebas de la tabla de decisión de
extensiones, de PDF, de Office y de zips.

## 2. Trazabilidad AC → pruebas

```powershell
.venv\Scripts\python.exe scripts\check_trazabilidad_ac.py --spec specs/005-analisis-adjuntos/spec.md
```

**Esperado**: exit 0 (cada AC-ADJ-NN del spec tiene al menos una prueba marcada).

## 3. Cobertura del paquete nuevo

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ --cov=src/level2_agent/adjuntos --cov-branch --cov-fail-under=80
```

**Esperado**: ≥ 80 % de líneas **y** ramas sobre `src/level2_agent/adjuntos/`
(Art. II.3).

## 4. Compuerta completa del repositorio

```powershell
.venv\Scripts\python.exe scripts\verify.py
```

**Esperado**: exit 0 (ruff, `mypy --strict`, pruebas con cobertura, longitud de
archivos, nombre de rama, pip-audit y compuertas ya existentes, sin bajar umbrales).

## 5. Demostración manual del comportamiento (positivo y negativo)

Construir adjuntos en memoria (nada se escribe a disco) y llamar `analizar_adjunto`.
Verificación esperada (detalle en [data-model.md](./data-model.md)):

| Escenario (payload + nombre) | Esperado |
|---|---|
| PDF válido con `/OpenAction` | `ADJ_PDF_ACTIVO`; hashes correctos |
| `factura.pdf.exe` (ejecutable) | `ADJ_EXTENSION_RIESGO` + `ADJ_DOBLE_EXTENSION` (AC-ADJ-03) |
| `.exe` renombrado a `.pdf` | `ADJ_TIPO_NO_COINCIDE` (firma exe concluyente, AC-ADJ-03) |
| Zip de ceros con relación 101:1 | aborto de la inspección + `ADJ_ARCHIVO_SOSPECHOSO`, sin agotar memoria (AC-ADJ-04) |
| Zip con contraseña | `ADJ_CIFRADO` (no se intenta leer el contenido) |
| Zip con 101 entradas o > 100 MiB | `ADJ_ARCHIVO_SOSPECHOSO` (aborto) |
| docx con `word/vbaProject.bin` | `ADJ_MACRO` |
| docx con `.rels` `TargetMode="External"` | `ADJ_ENLACE_EXTERNO` |
| EICAR (generado en memoria, nombre `eicar.com`) | `sha256 == EICAR_SHA256` publicado + `ADJ_EXTENSION_RIESGO` (AC-ADJ-02) |
| Payload vacío, truncado, nombre `../../x` o `C:\abs\x` | sin excepción; hashes válidos (AC-ADJ-06) |
| Cualquier análisis | el directorio de trabajo queda **vacío** (AC-ADJ-05) |

Un atajo cómodo sin escribir archivos: una celda de Python (o `python -c`) que
construya `payload = b"..."` o un zip con `zipfile` sobre `io.BytesIO`, llame
`analizar_adjunto("factura.pdf", "application/pdf", payload)` e imprima
`resultado.model_dump()`.

## 6. Verificación de que nada llega a disco ni se ejecuta (AC-ADJ-05)

Además de la prueba funcional (tmpdir vacío), la prueba de seguridad ejecuta un gate
AST sobre `src/level2_agent/adjuntos/*.py` que **prohíbe** `open(...)`,
`subprocess`, `os.startfile`, `webbrowser`, `shutil` y escrituras con `pathlib`
(D12). Se ejecuta como parte del paso 1; un fallo ahí indica que algún detector
rompió la garantía de memoria.

## [VERIFICAR] (Art. VI.3 — fuera de CI)

1. **olevba con file-like**: confirmar que `VBA_Parser` acepta `io.BytesIO` en la
   versión fijada 0.60.2 y los nombres exactos de los indicadores de enlace externo
   (research D6/[VERIFICAR] 1). Paso manual: analizar un `.doc` OLE2 real de muestra
   **en memoria** y comparar con el doble.
2. **Excepciones de pypdf con PDFs malformados**: recopilar 2–3 PDFs truncados
   reales y confirmar que todas sus excepciones caen en el `ADJ_ARCHIVO_SOSPECHOSO`
   del detector pdf (research D7/[VERIFICAR] 2).
3. **`filetype` con formatos ambiguos**: si la plantilla corporativa usa formatos que
   `filetype` no detecta, quedan como `tipo_real = "desconocido"` sin bandera (D5);
   documentar el caso en el informe final.
