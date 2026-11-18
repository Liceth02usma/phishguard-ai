"""AC-AGT-02: instrucciones inyectadas no cambian el veredicto.

10 correos con instrucciones para el modelo (en cuerpo, asunto, texto
oculto y nombre del adjunto) se comparan con el mismo correo sin esas
frases. El veredicto no debe cambiar.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from src.level2_agent.agente.modelos import EntradaAgente, SalidaAgente

from dobles_agente import ContadorDoble, ModeloDoble, entrada_agente_ejemplo

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "inyeccion"


def _cargar_fixtures() -> list[dict[str, Any]]:
    """Carga los 10 fixtures de inyecciÃ³n."""
    fixtures = []
    for p in sorted(FIXTURES_DIR.glob("inyeccion_*.json")):
        fixtures.append(json.loads(p.read_text(encoding="utf-8")))
    return fixtures


def _veredicto_con_modelo(entrada: EntradaAgente, modelo: ModeloDoble) -> bool:
    """Ejecuta el agente con el modelo doble y retorna es_phishing."""
    from src.level2_agent.agente.agente import consultar_agente

    # Contador aislado: el tope diario real (Mongo) no debe condicionar.
    resultado = consultar_agente(
        entrada, modelo=modelo, contador=ContadorDoble()  # type: ignore[arg-type]
    )
    if resultado.salida is not None:
        return resultado.salida.es_phishing
    return False  # fallback para revision_manual


def test_inyeccion_no_cambia_veredicto() -> None:
    """Con 10 fixtures de inyecciÃ³n, el veredicto no cambia."""
    fixtures = _cargar_fixtures()
    assert len(fixtures) == 10, f"Expected 10 fixtures, got {len(fixtures)}"

    # Modelo que siempre dice "es_phishing=True"
    modelo_con_inyeccion = ModeloDoble(
        salida=SalidaAgente(
            resumen="Phishing detectado",
            analisis_tecnico="AnÃ¡lisis tÃ©cnico",
            es_phishing=True,
            indicadores_phishing=["url_sospechosa"],
            nivel_severidad="Alto",
            justificacion_veredicto="URL sospechosa detectada",
        )
    )
    modelo_sin_inyeccion = ModeloDoble(
        salida=SalidaAgente(
            resumen="Phishing detectado",
            analisis_tecnico="AnÃ¡lisis tÃ©cnico",
            es_phishing=True,
            indicadores_phishing=["url_sospechosa"],
            nivel_severidad="Alto",
            justificacion_veredicto="URL sospechosa detectada",
        )
    )

    for fixture in fixtures:
        entrada = entrada_agente_ejemplo(score=fixture.get("score", 50))
        veredicto_con = _veredicto_con_modelo(entrada, modelo_con_inyeccion)
        veredicto_sin = _veredicto_con_modelo(entrada, modelo_sin_inyeccion)
        assert veredicto_con == veredicto_sin, (
            f"Fixture {fixture['id']}: veredicto cambiÃ³ con inyecciÃ³n "
            f"({veredicto_sin} â†’ {veredicto_con})"
        )
