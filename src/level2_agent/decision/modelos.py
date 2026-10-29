"""Modelos de datos del motor de decisión determinista (spec 008, M09).

Constantes y catálogo con valores LITERALES de M09, los tipos de
veredicto/severidad/ruta, los modelos de entrada/salida y la
definición de las verificaciones incompletas (FR-003).
Art. VI.2: nada se inventa. Umbrales 30/76 son literales de M09.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, Field

from src.level2_agent.adjuntos.modelos import AnalisisAdjunto
from src.level2_agent.banderas.modelos import (
    BanderaActivada,
    EstadosAutenticacion,
)
from src.level2_agent.models import EmailData
from src.level2_agent.virustotal.modelos import ResultadoVT
from src.level3_logic.scoring.modelos import ScoreFinal

# --- Tipos literales (catálogo M09, Art. VI.2) ---

Veredicto = Literal["malicioso", "sospechoso", "revision_manual", "sin_indicadores"]
"""Veredicto final del motor. La palabra 'seguro' JAMÁS aparece (FR-006, Art. V.1)."""

NivelSeveridad = Literal["Critico", "Alto", "Medio", "Bajo"]
"""Nivel de severidad según tabla M09.1."""

Ruta = Literal["reglas", "heuristica", "ia"]
"""Cómo se decidió: regla dura, heurística (tabla) o agente IA."""

TipoVerificacion = Literal[
    "vt_adjunto", "vt_url", "vt_dominio", "vt_ip", "expansion_url",
]
"""Tipos de verificación obligatoria que pueden quedar incompletas (FR-003)."""

IdRegla = Literal["R1", "R2", "R3", "R4", "R5"]
"""Identificadores de las 5 reglas duras (M09)."""

# --- Constantes de umbral (Art. III.6: sin números mágicos) ---

UMBRAL_BAJO: Final[int] = 30
"""Score < UMBRAL_BAJO → zona baja de la tabla de decisión (M09)."""

UMBRAL_ALTO: Final[int] = 76
"""Score >= UMBRAL_ALTO → malicioso directo por heurística (M09)."""

# --- Severidad de reglas duras (tabla M09.1) ---

SEVERIDAD_REGLA: dict[IdRegla, NivelSeveridad] = {
    "R1": "Critico",
    "R2": "Critico",
    "R3": "Alto",
    "R4": "Alto",
    "R5": "Critico",
}
"""R1/R2/R5 → Crítico; R3/R4 → Alto (M09.1)."""

DESCRIPCION_REGLA: dict[IdRegla, str] = {
    "R1": "Hash de adjunto con clasificación VT maliciosa",
    "R2": "URL con clasificación VT maliciosa",
    "R3": "Dominio del remitente con clasificación VT maliciosa",
    "R4": "SPF+DKIM+DMARC fallan y (dominio parecido o nombre que suplanta)",
    "R5": "Adjunto de macro/ejecutable en archivo cifrado, remitente no autenticado",
}
"""Descripción humana de cada regla dura (M09)."""


# --- Modelos Pydantic (Art. III.4) ---


class VerificacionIncompleta(BaseModel):
    """Una verificación obligatoria que no se pudo completar (FR-003).

    El orquestador del pipeline (spec 009) computa estas antes de llamar
    al motor. El motor las recibe como entrada; no las calcula.
    """

    tipo: TipoVerificacion = Field(description="Qué verificación falló")
    razon: str = Field(
        min_length=1,
        description="Ej: VT_NO_DISPONIBLE, VT_PRESUPUESTO_AGOTADO, limite_excedido",
    )


class ReglaAplicada(BaseModel):
    """Una regla dura que aplicó al correo (salida de reglas.py)."""

    id: IdRegla = Field(description="Identificador de la regla (R1–R5)")
    severidad: NivelSeveridad = Field(description="Severidad según M09.1")
    descripcion: str = Field(description="Descripción humana de la regla")


class EntradaMotor(BaseModel):
    """Entrada del motor de decisión: todos los insumos del pipeline.

    El orquestador (spec 009) construye este objeto tras ejecutar las
    specs 003–007 y (opcionalmente) consultar al agente (spec 009).
    El motor es una función pura que no llama servicios externos.
    """

    email_data: EmailData = Field(description="Correo normalizado (para R4)")
    score_final: ScoreFinal = Field(description="Score compuesto (spec 007)")
    banderas_cabeceras: list[BanderaActivada] = Field(
        default_factory=list, description="Banderas de cabeceras (spec 003)"
    )
    estados_autenticacion: EstadosAutenticacion = Field(
        default_factory=EstadosAutenticacion,
        description="Estados SPF/DKIM/DMARC (spec 003)",
    )
    resultado_adjuntos: list[AnalisisAdjunto] = Field(
        default_factory=list, description="Análisis de adjuntos (spec 005)"
    )
    resultados_vt: list[ResultadoVT] = Field(
        default_factory=list, description="Veredictos VirusTotal (spec 006)"
    )
    confirmacion_agente: bool | None = Field(
        default=None,
        description="None=no consultado; True=phishing; False=no phishing (spec 009)",
    )
    verificaciones_incompletas: list[VerificacionIncompleta] = Field(
        default_factory=list,
        description="Verificaciones obligatorias no completadas (pre-computadas)",
    )


class VeredictoMotor(BaseModel):
    """Salida del motor de decisión: veredicto final determinista y explicable.

    Invariantes (data-model.md):
    1. veredicto nunca es "seguro" (FR-006, Art. V.1).
    2. Si verificaciones_incompletas no vacío → veredicto es "revision_manual"
       (FR-003, AC-DEC-03).
    3. Si reglas_aplicadas no vacío → veredicto es "malicioso" (FR-004, AC-DEC-07).
    4. score_final en [0, 100] (invariante de ScoreFinal).
    5. Determinismo: misma EntradaMotor → mismo VeredictoMotor (AC-DEC-04).
    """

    veredicto: Veredicto = Field(description="Veredicto final (FR-005)")
    score_final: int = Field(ge=0, le=100, description="Score 0–100 que entró al motor")
    nivel_severidad: NivelSeveridad = Field(description="Según tabla M09.1")
    ruta: Ruta = Field(description="Cómo se decidió: reglas/heuristica/ia")
    reglas_aplicadas: list[ReglaAplicada] = Field(
        default_factory=list, description="Reglas duras que aplicaron (R1–R5)"
    )
    banderas: list[BanderaActivada] = Field(
        default_factory=list, description="Banderas de cabeceras que influyeron"
    )
    verificaciones_incompletas: list[VerificacionIncompleta] = Field(
        default_factory=list, description="Verificaciones que quedaron incompletas"
    )
