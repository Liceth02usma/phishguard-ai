"""Pruebas del detector de zips: cifrado, límites y aborto (FR-005).

Cifrado → ADJ_CIFRADO; >100 entradas → ADJ_ARCHIVO_SOSPECHOSO;
>límite descomprimido → ADJ_ARCHIVO_SOSPECHOSO; zip inválido →
ADJ_ARCHIVO_SOSPECHOSO; no-zip sin extensión zip → sin bandera.
"""

from __future__ import annotations

import io
import zipfile

from src.level2_agent.adjuntos import ConfigAdjuntos, analizar_adjunto


def _zip_n_entradas(n: int, contenido: bytes = b"x" * 100) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(n):
            zf.writestr(f"e{i}.txt", contenido)
    return buf.getvalue()


def _zip_cifrado() -> bytes:
    """Zip con flag de cifrado (bit 0) puesto manualmente en los bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("secret.txt", b"secreto")
    data = bytearray(buf.getvalue())
    # Patch local file header: flag general en offset 6 (2 bytes LE)
    idx = data.find(b"PK\x03\x04")
    if idx >= 0:
        data[idx + 6] |= 0x1
    # Patch central directory: flag en offset 8
    idx2 = data.find(b"PK\x01\x02")
    if idx2 >= 0:
        data[idx2 + 8] |= 0x1
    return bytes(data)


def _codigos(nombre: str, payload: bytes, config: ConfigAdjuntos | None = None) -> set[str]:
    r = analizar_adjunto(nombre, "application/zip", payload, config=config)
    return {b.codigo for b in r.banderas}


def test_zip_cifrado_activa_adj_cifrado() -> None:
    c = _codigos("secret.zip", _zip_cifrado())
    assert "ADJ_CIFRADO" in c


def test_zip_100_entradas_ok() -> None:
    c = _codigos("normal.zip", _zip_n_entradas(100))
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in c


def test_zip_101_entradas_sospechoso() -> None:
    c = _codigos("many.zip", _zip_n_entradas(101))
    assert "ADJ_ARCHIVO_SOSPECHOSO" in c


def test_zip_limite_descomprimido_borde() -> None:
    """Con config de límite pequeño, el borde exacto no activa bandera."""
    config = ConfigAdjuntos.defecto()
    config = config.model_copy(update={"limite_descomprimido_zip": 1000})
    # Un zip con contenido de exactamente 1000 bytes
    payload = b"a" * 1000
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("d.txt", payload)
    c = _codigos("edge.zip", buf.getvalue(), config=config)
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in c


def test_zip_sobre_limite_descomprimido_sospechoso() -> None:
    """Con config de límite pequeño, pasarse activa ADJ_ARCHIVO_SOSPECHOSO."""
    config = ConfigAdjuntos.defecto()
    config = config.model_copy(update={"limite_descomprimido_zip": 500})
    payload = b"a" * 1000
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("d.txt", payload)
    c = _codigos("over.zip", buf.getvalue(), config=config)
    assert "ADJ_ARCHIVO_SOSPECHOSO" in c


def test_zip_invalido_activa_sospechoso() -> None:
    """Un .zip que no es un zip válido activa ADJ_ARCHIVO_SOSPECHOSO."""
    c = _codigos("fake.zip", b"esto no es un zip")
    assert "ADJ_ARCHIVO_SOSPECHOSO" in c


def test_no_zip_sin_extension_zip_sin_bandera() -> None:
    """Un payload no-zip con nombre no-zip no activa banderas de zip."""
    r = analizar_adjunto("data.bin", "application/octet-stream", b"datos aleatorios")
    codigos = {b.codigo for b in r.banderas}
    assert "ADJ_ARCHIVO_SOSPECHOSO" not in codigos
    assert "ADJ_CIFRADO" not in codigos
