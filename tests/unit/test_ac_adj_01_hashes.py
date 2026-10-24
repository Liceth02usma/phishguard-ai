"""AC-ADJ-01: SHA-256 coincide con referencias externas para 3 archivos de prueba.

Los hashes de referencia son constantes publicadas (no calculadas con hashlib
en runtime — eso haría la prueba circular). Verifica también MD5 y SHA-1.
"""

from __future__ import annotations

import pytest
from src.level2_agent.adjuntos import analizar_adjunto

# Referencias publicadas (NIST FIPS 180-4 test vectors y conocidas).
_REF_EMPTY = {
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "md5": "d41d8cd98f00b204e9800998ecf8427e",
    "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
}
_REF_HELLO = {
    "sha256": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    "md5": "5eb63bbbe01eeed093cb22bb8f5acdc3",
    "sha1": "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed",
}
_REF_ABC = {
    "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "md5": "900150983cd24fb0d6963f7d28e17f72",
    "sha1": "a9993e364706816aba3e25717850c26c9cd0d89d",
}


@pytest.mark.ac("AC-ADJ-01")
def test_sha256_vacio() -> None:
    r = analizar_adjunto("vacio.txt", "text/plain", b"")
    assert r.sha256 == _REF_EMPTY["sha256"]
    assert r.md5 == _REF_EMPTY["md5"]
    assert r.sha1 == _REF_EMPTY["sha1"]


@pytest.mark.ac("AC-ADJ-01")
def test_sha256_hello_world() -> None:
    r = analizar_adjunto("hello.txt", "text/plain", b"hello world")
    assert r.sha256 == _REF_HELLO["sha256"]
    assert r.md5 == _REF_HELLO["md5"]
    assert r.sha1 == _REF_HELLO["sha1"]


@pytest.mark.ac("AC-ADJ-01")
def test_sha256_abc() -> None:
    r = analizar_adjunto("abc.txt", "text/plain", b"abc")
    assert r.sha256 == _REF_ABC["sha256"]
    assert r.md5 == _REF_ABC["md5"]
    assert r.sha1 == _REF_ABC["sha1"]


@pytest.mark.ac("AC-ADJ-01")
def test_hashes_formato_valido() -> None:
    """Los hashes siempre son hex válido de 64/32/40 chars, incluso para payload vacío."""
    r = analizar_adjunto("x.bin", "application/octet-stream", b"\x00\xff\x10")
    assert len(r.sha256) == 64 and all(c in "0123456789abcdef" for c in r.sha256)
    assert len(r.md5) == 32 and all(c in "0123456789abcdef" for c in r.md5)
    assert len(r.sha1) == 40 and all(c in "0123456789abcdef" for c in r.sha1)
