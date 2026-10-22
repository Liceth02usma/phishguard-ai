"""Pruebas para la compuerta de secretos (AC-CAL-04).

Una cadena con forma de clave de API debe detectarse. La lógica de
decisión es pura; la integración con gitleaks se prueba si el binario
está disponible (skip en caso contrario — no xfail, Art. II.7).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from scripts.verify import evaluar_secretos

# Una cadena con forma de AWS Access Key ID (prefijo AKIA + 16 alfanum).
CLAVE_API = "AKIAIOSFODNN7EXAMPLE"


@pytest.mark.ac("AC-CAL-04")
def test_hallazgo_positivo_falla() -> None:
    """Si gitleaks reporta hallazgos, la compuerta falla."""
    resultado = evaluar_secretos(hallazgos=1)
    assert resultado.ok is False
    assert len(resultado.detalles) >= 1


@pytest.mark.ac("AC-CAL-04")
def test_sin_hallazgos_pasa() -> None:
    resultado = evaluar_secretos(hallazgos=0)
    assert resultado.ok is True


@pytest.mark.ac("AC-CAL-04")
def test_gitleaks_detecta_clave_en_archivo(tmp_path: Path) -> None:
    """Integración: gitleaks detecta una clave en un archivo temporal."""
    if shutil.which("gitleaks") is None:
        pytest.skip("gitleaks no está instalado; se requiere para esta prueba integrada")

    archivo = tmp_path / "secreto.py"
    archivo.write_text(f"api_key = {CLAVE_API!r}\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "gitleaks",
            "detect",
            "--source",
            str(tmp_path),
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            str(tmp_path / "report.json"),
        ],
        capture_output=True,
        text=True,
    )
    # gitleaks exit 1 cuando encuentra hallazgos
    assert proc.returncode == 1, (
        f"gitleaks debió detectar la clave. stdout={proc.stdout} stderr={proc.stderr}"
    )
