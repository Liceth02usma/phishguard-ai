"""Cálculo de hashes de adjuntos en memoria (FR-001).

SHA-256 es el hash principal; MD5 y SHA-1 son informativos. Todo sobre bytes
en memoria (FR-006: sin escritura a disco).
"""

from __future__ import annotations

import hashlib


def calcular_hashes(payload: bytes) -> tuple[str, str, str]:
    """Calcula SHA-256, MD5 y SHA-1 del payload (FR-001).

    Args:
        payload: bytes del adjunto en memoria.

    Returns:
        Tupla (sha256, md5, sha1) en hexadecimal minúsculo.
    """
    return (
        hashlib.sha256(payload).hexdigest(),
        hashlib.md5(payload).hexdigest(),
        hashlib.sha1(payload).hexdigest(),
    )
