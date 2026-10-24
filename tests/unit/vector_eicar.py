"""Vector de prueba EICAR (spec 005, AC-ADJ-02, SC-003).

Genera la cadena estándar EICAR **en memoria** (nunca un archivo en disco).
Importable por la spec 006 para su prueba integrada de VirusTotal con respuesta
grabada (research D9).
"""

from __future__ import annotations

EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
"""Hash SHA-256 publicado de la cadena EICAR (constante, no calculada en runtime)."""

# Cadena estándar EICAR (68 bytes ASCII, inofensiva). Raw string para el backslash.
_EICAR_CADENA = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def generar_eicar() -> bytes:
    """Devuelve la cadena estándar EICAR como bytes (en memoria, nunca en disco)."""
    return _EICAR_CADENA.encode("ascii")
