"""Análisis de archivos zip con límites duros (FR-005).

`zipfile` stdlib sobre `io.BytesIO`: límites de 100 entradas, 100 MiB
descomprimidos y relación 100:1. Lectura por **streaming con tope duro**
(never trust declared sizes — research D8). Cifrado → `ADJ_CIFRADO`.
Todo aborta antes de agotar memoria (SC-002/AC-ADJ-04).
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

from src.level2_agent.adjuntos.modelos import (
    BanderaAdjunto,
    ContextoAdjunto,
    ResultadoDetector,
    bandera,
)

if TYPE_CHECKING:
    from src.level2_agent.adjuntos.configuracion import ConfigAdjuntos

_EXT_ZIP = frozenset({"zip"})
_TAMANO_CHUNK = 8192


class ComprimidosDetector:
    """Detector de zips peligrosos con límites (FR-005)."""

    def evaluar(self, ctx: ContextoAdjunto) -> ResultadoDetector:
        ext = ctx.extension_final.lower().lstrip(".")
        es_zip = ext in _EXT_ZIP or ctx.tipo_real == "zip"
        if not es_zip:
            return ResultadoDetector((), ())

        payload = ctx.payload
        cfg = ctx.config
        banderas: list[BanderaAdjunto] = []
        detalles: list[str] = []

        try:
            zf = zipfile.ZipFile(io.BytesIO(payload))
        except Exception as exc:  # noqa: BLE001 — BadZipFile y otros
            banderas.append(bandera("ADJ_ARCHIVO_SOSPECHOSO", "zip no parseable"))
            detalles.append(f"zipfile fallo: {type(exc).__name__}")
            return ResultadoDetector(tuple(banderas), tuple(detalles))

        with zf:
            infos = zf.infolist()

            if len(infos) > cfg.limite_entradas_zip:
                banderas.append(
                    bandera(
                        "ADJ_ARCHIVO_SOSPECHOSO",
                        f"{len(infos)} entradas exceden el limite",
                    )
                )
                return ResultadoDetector(tuple(banderas), tuple(detalles))

            for info in infos:
                if info.flag_bits & 0x1:
                    if not any(b.codigo == "ADJ_CIFRADO" for b in banderas):
                        banderas.append(bandera("ADJ_CIFRADO", "zip cifrado con contrasena"))
                    break

            if self._pre_check_limites(infos, cfg, banderas):
                return ResultadoDetector(tuple(banderas), tuple(detalles))

            self._streaming_read(zf, infos, cfg, banderas, detalles)

        return ResultadoDetector(tuple(banderas), tuple(detalles))

    def _pre_check_limites(
        self,
        infos: list[zipfile.ZipInfo],
        cfg: ConfigAdjuntos,
        banderas: list[BanderaAdjunto],
    ) -> bool:
        """Pre-check de tamaños y relaciones declaradas. True si hay aborto."""
        total_declarado = 0
        for info in infos:
            total_declarado += info.file_size
            if info.compress_size > 0:
                if info.file_size > cfg.ratio_maximo_zip * info.compress_size:
                    banderas.append(
                        bandera("ADJ_ARCHIVO_SOSPECHOSO", "relacion de compresion excede el limite")
                    )
                    return True
            elif info.file_size > 0:
                banderas.append(
                    bandera("ADJ_ARCHIVO_SOSPECHOSO", "relacion infinita (compress_size 0)")
                )
                return True

        if total_declarado > cfg.limite_descomprimido_zip:
            banderas.append(
                bandera("ADJ_ARCHIVO_SOSPECHOSO", "tamano descomprimido declarado excede el limite")
            )
            return True
        return False

    def _streaming_read(
        self,
        zf: zipfile.ZipFile,
        infos: list[zipfile.ZipInfo],
        cfg: ConfigAdjuntos,
        banderas: list[BanderaAdjunto],
        detalles: list[str],
    ) -> None:
        """Lee por streaming con tope duro (catches lying zips, D8)."""
        total_real = 0
        for info in infos:
            if info.flag_bits & 0x1 or info.is_dir():
                continue
            try:
                with zf.open(info) as f:
                    while True:
                        chunk = f.read(_TAMANO_CHUNK)
                        if not chunk:
                            break
                        total_real += len(chunk)
                        if total_real > cfg.limite_descomprimido_zip:
                            if not any(
                                b.codigo == "ADJ_ARCHIVO_SOSPECHOSO" for b in banderas
                            ):
                                banderas.append(
                                    bandera(
                                        "ADJ_ARCHIVO_SOSPECHOSO",
                                        "descompresion real excede el limite",
                                    )
                                )
                            return
            except Exception as exc:  # noqa: BLE001 — entrada no legible
                detalles.append(f"entrada zip no legible: {type(exc).__name__}")
