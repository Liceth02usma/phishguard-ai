"""Pruebas de los CLI main() y de los wrappers internos de verify.py.

Usan monkeypatch para no invocar subprocess reales (Art. II.5 — sin red).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import scripts.check_longitud_archivos as mod_long
import scripts.check_nombre_rama as mod_rama
import scripts.check_trazabilidad_ac as mod_traz
import scripts.verify as mod_verify
from scripts._comunes import ResultadoCompuerta, ResultadoVerify

# --- check_longitud_archivos.main ---


def test_main_longitud_pasa_capsys(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    ok = tmp_path / "ok.py"
    ok.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(mod_long, "_coleccionar_py", lambda _dirs: [ok])
    assert mod_long.main() == 0
    out = capsys.readouterr().out
    assert "[PASS]" in out


def test_main_longitud_falla_capsys(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    mal = tmp_path / "mal.py"
    mal.write_text("\n".join(f"x = {i}" for i in range(600)) + "\n", encoding="utf-8")
    monkeypatch.setattr(mod_long, "_coleccionar_py", lambda _dirs: [mal])
    assert mod_long.main() == 1
    out = capsys.readouterr().out
    assert "[FAIL]" in out


# --- check_nombre_rama.main ---


def test_main_nombre_rama_pasa(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(mod_rama, "rama_actual", lambda: "feature/x")
    assert mod_rama.main() == 0
    assert "[PASS]" in capsys.readouterr().out


def test_main_nombre_rama_falla(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(mod_rama, "rama_actual", lambda: "Feature/x")
    assert mod_rama.main() == 1
    assert "[FAIL]" in capsys.readouterr().out


def test_main_nombre_rama_error_git(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _boom() -> str:
        raise RuntimeError("git no disponible")

    monkeypatch.setattr(mod_rama, "rama_actual", _boom)
    assert mod_rama.main() == 1


# --- check_trazabilidad_ac.main ---


def test_main_trazabilidad_pasa(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("**AC-CAL-01**: algo.\n", encoding="utf-8")
    monkeypatch.setattr(
        mod_traz, "_leer_pruebas", lambda _dirs: '@pytest.mark.ac("AC-CAL-01")\n'
    )
    assert mod_traz.main(str(spec)) == 0


def test_main_trazabilidad_falla(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("**AC-CAL-01**: algo.\n**AC-CAL-02**: otro.\n", encoding="utf-8")
    monkeypatch.setattr(mod_traz, "_leer_pruebas", lambda _dirs: '@pytest.mark.ac("AC-CAL-01")\n')
    assert mod_traz.main(str(spec)) == 1
    assert "AC-CAL-02" in capsys.readouterr().out


def test_main_trazabilidad_sin_spec_arg(capsys: pytest.CaptureFixture[str]) -> None:
    assert mod_traz.main(None) == 1  # sin --spec en sys.argv


# --- verify._run ---


def test_run_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    ok, _ = mod_verify._run(["echo", "hi"])
    assert ok is True


def test_run_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "bad"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    ok, _ = mod_verify._run(["false"])
    assert ok is False


def test_run_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*a: object, **k: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["x"], timeout=1)

    monkeypatch.setattr(subprocess, "run", _boom)
    ok, _ = mod_verify._run(["sleep", "999"], timeout=1)
    assert ok is False


# --- verify._compuerta_* (con subprocess monkeypatched) ---


def test_compuerta_cobertura_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    res = mod_verify._compuerta_cobertura()
    assert res.ok is True


def test_compuerta_cobertura_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "low"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    res = mod_verify._compuerta_cobertura()
    assert res.ok is False


def test_compuerta_secretos_sin_gitleaks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _x: None)
    res = mod_verify._compuerta_secretos()
    assert res.ok is True  # degrada a pass con aviso localmente; CI la ejecuta
    assert "omitida" in res.detalles[0]


def test_compuerta_secretos_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _x: "/usr/bin/gitleaks")

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    res = mod_verify._compuerta_secretos()
    assert res.ok is True


def test_compuerta_lint_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    assert mod_verify._compuerta_lint().ok is True


def test_compuerta_tipos_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "type error"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    assert mod_verify._compuerta_tipos().ok is False


def test_compuerta_dependencias_sin_pip_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod_verify, "_pip_audit_disponible", lambda: False)
    monkeypatch.setattr(shutil, "which", lambda _x: None)
    res = mod_verify._compuerta_dependencias()
    assert res.ok is True  # degrada a pass con aviso localmente; CI la ejecuta
    assert "omitida" in res.detalles[0]


def test_compuerta_dependencias_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod_verify, "_pip_audit_disponible", lambda: True)

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc())
    assert mod_verify._compuerta_dependencias().ok is True


def test_compuerta_longitud() -> None:
    """Ejecuta sobre el repo real (todos los archivos < 500 líneas → ok)."""
    res = mod_verify._compuerta_longitud()
    assert res.nombre == "longitud_archivos"
    assert res.ok is True


def test_compuerta_nombre_rama_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod_verify, "rama_actual", lambda: "main")
    assert mod_verify._compuerta_nombre_rama().ok is True


def test_compuerta_nombre_rama_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> str:
        raise RuntimeError("no git")

    monkeypatch.setattr(mod_verify, "rama_actual", _boom)
    assert mod_verify._compuerta_nombre_rama().ok is False


def test_compuerta_trazabilidad_spec_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    res = mod_verify._compuerta_trazabilidad()
    assert res.ok is True  # omitida


# --- verify.ejecutar y main ---


def test_ejecutar_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mod_verify,
        "COMPUERTAS",
        [
            ("a", lambda: ResultadoCompuerta("a", True)),
            ("b", lambda: ResultadoCompuerta("b", False, ["x"])),
        ],
    )
    res = mod_verify.ejecutar()
    assert res.ok is False
    assert len(res.resultados) == 2


def test_ejecutar_solo_una(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mod_verify,
        "COMPUERTAS",
        [
            ("a", lambda: ResultadoCompuerta("a", True)),
            ("b", lambda: ResultadoCompuerta("b", False)),
        ],
    )
    res = mod_verify.ejecutar(solo="a")
    assert len(res.resultados) == 1


def test_ejecutar_sin_cobertura(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mod_verify,
        "COMPUERTAS",
        [
            ("cobertura", lambda: ResultadoCompuerta("cobertura", False)),
            ("lint", lambda: ResultadoCompuerta("lint", True)),
        ],
    )
    res = mod_verify.ejecutar(sin_cobertura=True)
    assert len(res.resultados) == 1


def test_main_ok(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        mod_verify,
        "ejecutar",
        lambda **k: ResultadoVerify([], True, "ok"),
    )
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["verify.py"])
    assert mod_verify.main() == 0


def test_main_falla(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        mod_verify,
        "ejecutar",
        lambda **k: ResultadoVerify([], False, "fail"),
    )
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["verify.py"])
    assert mod_verify.main() == 1
