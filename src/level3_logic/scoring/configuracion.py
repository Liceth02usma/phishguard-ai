"""Configuración del scoring (spec 007): ConfigScoring + env vars."""

from __future__ import annotations

import os
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent.parent.parent.parent
RUTA_MODELO_POR_DEFECTO = PROYECTO / "data" / "modelo" / "clasificador_v1.json"

# Proveedores de confianza por defecto (research D5)
PROVEEDORES_CONFIANZA_POR_DEFECTO: tuple[str, ...] = (
    "google.com", "microsoft.com", "apple.com", "amazon.com",
    "paypal.com", "visa.com", "mastercard.com",
    "bbva.com", "santander.com", "banco.com",
    "sendgrid.net", "mailchimp.com", "amazonses.com",
    "office365.us", "outlook.com",
)


class ConfigScoring:
    """Configuración inyectable para el scoring.

    Lee de entorno: DOMINIOS_PROPIOS, DOMINIOS_PROVEEDORES_CONFIANZA, RUTA_MODELO.
    """

    def __init__(
        self,
        dominios_propios: tuple[str, ...] = (),
        proveedores_confianza: tuple[str, ...] = (),
        ruta_modelo: Path = RUTA_MODELO_POR_DEFECTO,
    ) -> None:
        self.dominios_propios = dominios_propios
        self.proveedores_confianza = proveedores_confianza or PROVEEDORES_CONFIANZA_POR_DEFECTO
        self.ruta_modelo = ruta_modelo

    @classmethod
    def desde_entorno(cls) -> ConfigScoring:
        """Crea ConfigScoring desde variables de entorno.

        Env vars:
            DOMINIOS_PROPIOS: lista separada por coma.
            DOMINIOS_PROVEEDORES_CONFIANZA: lista separada por coma.
            RUTA_MODELO: ruta al archivo JSON del modelo.

        Raises:
            ScoringError: si alguna variable tiene formato inválido.
        """
        dominios_propios = _leer_lista_env("DOMINIOS_PROPIOS")
        proveedores = _leer_lista_env("DOMINIOS_PROVEEDORES_CONFIANZA")
        ruta_str = os.environ.get("RUTA_MODELO", "").strip()
        ruta_modelo = Path(ruta_str) if ruta_str else RUTA_MODELO_POR_DEFECTO
        return cls(
            dominios_propios=tuple(dominios_propios),
            proveedores_confianza=tuple(proveedores) if proveedores else (),
            ruta_modelo=ruta_modelo,
        )


def _leer_lista_env(nombre: str) -> list[str]:
    """Lee una variable de entorno como lista separada por coma."""
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return []
    return [v.strip().lower() for v in valor.split(",") if v.strip()]
