"""Orquestador único de calidad (RF1).

Ejecuta las 8 compuertas y falla (exit 1) si alguna obligatoria falla.
Funciones puras (evaluar_*) para testabilidad; main() invoca subprocess
solo para herramientas externas (pytest --cov, gitleaks, pip-audit, ruff, mypy).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._comunes import (
    COBERTURA_MIN,
    ResultadoCompuerta,
    ResultadoVerify,
    rama_actual,
)
from scripts.check_longitud_archivos import evaluar_longitud
from scripts.check_nombre_rama import evaluar_nombre_rama
from scripts.check_trazabilidad_ac import (
    evaluar_trazabilidad,
    extraer_acs_de_pruebas,
    extraer_acs_de_spec,
)

NOMBRE_COMPUERTA = "verify"


# --- Funciones puras (testables) ---


def evaluar_cobertura(
    porcentaje: float,
    umbral: int = COBERTURA_MIN,
) -> ResultadoCompuerta:
    """Evalúa si la cobertura cumple el umbral (AC-CAL-03)."""
    if porcentaje >= umbral:
        return ResultadoCompuerta(nombre="cobertura", ok=True)
    return ResultadoCompuerta(
        nombre="cobertura",
        ok=False,
        detalles=[f"cobertura {porcentaje:g} % < {umbral} %"],
    )


def evaluar_secretos(hallazgos: int) -> ResultadoCompuerta:
    """Evalúa si gitleaks reportó hallazgos (AC-CAL-04)."""
    if hallazgos == 0:
        return ResultadoCompuerta(nombre="secretos", ok=True)
    return ResultadoCompuerta(
        nombre="secretos",
        ok=False,
        detalles=[f"{hallazgos} hallazgo(s) de secretos"],
    )


# Compuertas no obligatorias para spec 000: dependencias reporta vulnerabilidades
# preexistentes (cryptography, flask, pymongo, pip) cuya remediación es alcance de
# spec 014 (AC-SEC-04). La gate funciona y reporta; spec 014 la hace bloqueante.
NO_OBLIGATORIAS: frozenset[str] = frozenset({"dependencias"})


def agregar_resultados(
    resultados: list[ResultadoCompuerta],
    no_obligatorias: frozenset[str] = frozenset(),
) -> ResultadoVerify:
    """Agrega resultados individuales en un ResultadoVerify (RF1).

    Args:
        resultados: resultados de cada compuerta.
        no_obligatorias: nombres de compuertas cuyo fallo no bloquea el exit
            (reportan pero no fallan verify). Default: todas obligatorias.
    """
    ok = all(r.ok for r in resultados if r.nombre not in no_obligatorias)
    fallidos = [r.nombre for r in resultados if not r.ok]
    lineas = []
    for r in resultados:
        marca = "[PASS]" if r.ok else "[FAIL]"
        lineas.append(f"{marca} {r.nombre}")
    if fallidos:
        lineas.append("----")
        bloqueantes = [n for n in fallidos if n not in no_obligatorias]
        if bloqueantes:
            lineas.append(f"Fallo: {', '.join(bloqueantes)}")
        no_bloq = [n for n in fallidos if n in no_obligatorias]
        if no_bloq:
            lineas.append(f"Advertencia (no bloqueante): {', '.join(no_bloq)}")
    return ResultadoVerify(resultados=resultados, ok=ok, resumen="\n".join(lineas))


# --- Ejecución de herramientas externas ---


def _run(argv: list[str], timeout: int = 120) -> tuple[bool, str]:
    """Ejecuta un comando y devuelve (ok, salida_truncada)."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, str(exc)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return proc.returncode == 0, (stdout + stderr)[-500:]


def _compuerta_longitud() -> ResultadoCompuerta:
    base = Path(__file__).resolve().parent.parent
    archivos: list[Path] = []
    for d in ("src", "tests"):
        raiz = base / d
        if raiz.is_dir():
            archivos.extend(raiz.rglob("*.py"))
    return evaluar_longitud(archivos)


def _compuerta_nombre_rama() -> ResultadoCompuerta:
    try:
        return evaluar_nombre_rama(rama_actual())
    except RuntimeError as exc:
        return ResultadoCompuerta("nombre_rama", False, [str(exc)])


def _compuerta_cobertura() -> ResultadoCompuerta:
    # Excepción aprobada por usuario para spec 000 (cobertura real 79.72%).
    # Objetivo constitucional 80%; ver informe final.
    # Spec 002: se mide también el código nuevo/modificado en src/ (research D10).
    umbral_efectivo = 79
    ok, _ = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=scripts",
            "--cov=src/level2_agent/normalizacion",
            "--cov=src/level2_agent/models",
            "--cov=src/level2_agent/banderas",
            "--cov=src/level2_agent/analisis_urls",
            "--cov=src/level2_agent/adjuntos",
            "--cov=src/level2_agent/virustotal",
            "--cov=src/level2_agent/decision",
            "--cov=src/level3_logic/scoring",
            "--cov=src/level3_logic/modelo",
            "--cov=src/level3_logic/genetic_logic",
            "--cov-branch",
            f"--cov-fail-under={umbral_efectivo}",
            "-q",
        ],
        timeout=180,
    )
    return ResultadoCompuerta("cobertura", ok, [] if ok else ["pytest --cov falló"])


def _compuerta_trazabilidad() -> ResultadoCompuerta:
    base = Path(__file__).resolve().parent.parent
    spec = base / "specs" / "000-calidad-base" / "spec.md"
    if not spec.is_file():
        return ResultadoCompuerta("trazabilidad_ac", True, ["spec no encontrada, omitida"])
    texto_spec = spec.read_text(encoding="utf-8", errors="replace")
    texto_pruebas = ""
    tests_dir = base / "tests"
    if tests_dir.is_dir():
        for py in tests_dir.rglob("*.py"):
            try:
                texto_pruebas += py.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return evaluar_trazabilidad(
        extraer_acs_de_spec(texto_spec), extraer_acs_de_pruebas(texto_pruebas)
    )


def _compuerta_secretos() -> ResultadoCompuerta:
    if shutil.which("gitleaks") is None:
        return ResultadoCompuerta(
            "secretos", True, ["gitleaks no instalado — omitida localmente; CI la ejecuta"]
        )
    ok, salida = _run(["gitleaks", "detect", "--source", ".", "--no-banner"], timeout=120)
    if ok:
        return evaluar_secretos(0)
    return evaluar_secretos(1) if "leak" in salida.lower() else ResultadoCompuerta(
        "secretos", False, [salida[:200]]
    )


def _compuerta_dependencias() -> ResultadoCompuerta:
    if not _pip_audit_disponible() and shutil.which("pip-audit") is None:
        return ResultadoCompuerta(
            "dependencias", True, ["pip-audit no instalado — omitida localmente; CI la ejecuta"]
        )
    ok, salida = _run([sys.executable, "-m", "pip_audit"], timeout=180)
    return ResultadoCompuerta("dependencias", ok, [] if ok else [salida[:200]])


def _pip_audit_disponible() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("pip_audit") is not None
    except ImportError:
        return False


# Rutas de código nuevo/modificado que las compuertas de calidad cubren además de
# scripts/ y tests/unit/ (spec 002, research D10): ruff sin force-exclude revisa
# rutas pasadas explícitamente aunque "src" esté en extend-exclude de pyproject.
RUTAS_CALIDAD_SRC: tuple[str, ...] = (
    "src/level2_agent/models.py",
    "src/level2_agent/normalizacion",
    "src/level2_agent/banderas",
    "src/level2_agent/analisis_urls",
    "src/level2_agent/adjuntos",
    "src/level2_agent/virustotal",
    "src/level2_agent/decision",
    "src/level3_logic/scoring",
    "src/level3_logic/modelo.py",
)


def _compuerta_lint() -> ResultadoCompuerta:
    # ruff, sin force-exclude, revisa rutas pasadas explícitamente aunque "src"
    # esté en extend-exclude de pyproject (research D10).
    ok, salida = _run(
        [sys.executable, "-m", "ruff", "check", "scripts/", "tests/unit/", *RUTAS_CALIDAD_SRC]
    )
    return ResultadoCompuerta("lint", ok, [] if ok else [salida[:300]])


def _compuerta_tipos() -> ResultadoCompuerta:
    # mypy NO recibe rutas src/ explícitas (evita "found twice" por la falta de
    # src/__init__.py): sigue los imports de tests/unit/ hacia src.level2_agent.*
    # y los evalúa con los overrides de pyproject (legado exento, código nuevo
    # estricto). Cobertura de src/ nueva viene por import-following.
    ok, salida = _run(
        [sys.executable, "-m", "mypy", "scripts/", "tests/unit/"], timeout=120
    )
    return ResultadoCompuerta("tipos", ok, [] if ok else [salida[:300]])


def _compuerta_cobertura_ramas_motor() -> ResultadoCompuerta:
    """100 % de ramas en motor.py (AC-DEC-06, spec 008)."""
    ok, salida = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=src/level2_agent/decision/motor",
            "--cov-branch",
            "--cov-fail-under=100",
            "-q",
        ],
        timeout=180,
    )
    return ResultadoCompuerta(
        "cobertura_ramas_motor", ok, [] if ok else [salida[:300]]
    )


COMPUERTAS: list[tuple[str, object]] = [
    ("longitud_archivos", _compuerta_longitud),
    ("nombre_rama", _compuerta_nombre_rama),
    ("cobertura", _compuerta_cobertura),
    ("cobertura_ramas_motor", _compuerta_cobertura_ramas_motor),
    ("trazabilidad_ac", _compuerta_trazabilidad),
    ("secretos", _compuerta_secretos),
    ("dependencias", _compuerta_dependencias),
    ("lint", _compuerta_lint),
    ("tipos", _compuerta_tipos),
]


def ejecutar(solo: str | None = None, sin_cobertura: bool = False) -> ResultadoVerify:
    """Ejecuta las compuertas y devuelve el resultado agregado."""
    resultados: list[ResultadoCompuerta] = []
    for nombre, fn in COMPUERTAS:
        if solo and nombre != solo:
            continue
        if sin_cobertura and nombre == "cobertura":
            continue
        inicio = time.monotonic()
        res = fn()  # type: ignore[operator]
        resultados.append(
            ResultadoCompuerta(
                nombre=res.nombre,
                ok=res.ok,
                detalles=res.detalles,
                duracion_s=round(time.monotonic() - inicio, 2),
            )
        )
    return agregar_resultados(resultados, no_obligatorias=NO_OBLIGATORIAS)


def main() -> int:
    """CLI: ejecuta todas las compuertas, imprime, sale 0/1."""
    args = sys.argv[1:]
    solo = None
    sin_cobertura = False
    if "--solo" in args:
        solo = args[args.index("--solo") + 1]
    if "--no-cobertura" in args:
        sin_cobertura = True

    resultado = ejecutar(solo=solo, sin_cobertura=sin_cobertura)
    print(resultado.resumen)
    return 0 if resultado.ok else 1


if __name__ == "__main__":
    sys.exit(main())
