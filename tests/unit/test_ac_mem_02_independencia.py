"""AC-MEM-02: analizar 5 correos en dos órdenes produce los mismos resultados.

Regresión del defecto D1 del plan maestro (contaminación entre correos):
cada correo se analiza solo con su propia evidencia (FR-002, SC-001).

Los correos son SINTÉTICOS y deterministas (Art. 0 — son datos de prueba, no
instrucciones). Las puntuaciones se miden con el algoritmo genético real y se
verifican por banda antes de comparar órdenes:

- benignos A y B: suma de pesos negativa (``apelacion_miedo`` ± ``telefono``
  / ``envio_madrugada``) → score < 30
- medios C y D: ``cuerpo_corto`` (0.935) y ``dominio_externo`` (0.355) →
  30 ≤ score ≤ 75 (ruta del agente, donde existía la memoria)
- malicioso E: ``cuerpo_corto`` + ``accion_legal`` (1.87) → score > 75

Ver research.md D7 (mecanismo de rojo) y D11 (medición empírica de bandas).
"""

from __future__ import annotations

from typing import Any

import pytest
from src.level2_agent import agent as mod_agent
from src.level2_agent.models import EmailData

FIXTURES = [
    # A — benigno: cuerpo ≥ 50 palabras, "riesgo" (miedo) + teléfono → suma -1.419
    {
        "id": "correo_a",
        "subject": "Actualización del informe trimestral",
        "recipient": "ana@empresa.com",
        "textBody": (
            "Hola equipo: les recordamos que el informe trimestral de operaciones "
            "debe consolidarse antes del cierre del mes. El documento incluye el "
            "resumen de métricas del periodo, las conclusiones del comité y las "
            "recomendaciones del área técnica. Por favor revisen los apartados "
            "correspondientes a su departamento y envíen sus comentarios por el "
            "canal interno. Cualquier observación sobre el riesgo operativo debe "
            "registrarse en el sistema de gestión para su seguimiento. La reunión "
            "de revisión se realizará el próximo martes a las diez de la mañana en "
            "la sala de juntas principal. Recuerden que la asistencia es obligatoria "
            "para los responsables de cada unidad y que deben llevar impreso el "
            "borrador del documento. Si no pueden asistir, avisen con antelación al "
            "coordinador del proyecto. El número de referencia interna de este "
            "proceso es 3051234567 y debe citarse en cualquier comunicación "
            "relacionada con esta iniciativa. Gracias por su colaboración y "
            "compromiso habitual con el trabajo del equipo."
        ),
        "htmlBody": "",
        "headers": (
            '{"From": "soporte@empresa.com", '
            '"Date": "Tue, 15 Oct 2024 12:30:00 +0000"}'
        ),
        "esperada": "benigna",
    },
    # B — benigno: cuerpo ≥ 50 palabras, "perder" (miedo) + envío 02:00 → suma -1.226
    {
        "id": "correo_b",
        "subject": "Nuevas pautas de coordinación interna",
        "recipient": "equipo@empresa.com",
        "textBody": (
            "Estimadas compañeras: por medio de la presente queremos informarles "
            "sobre las nuevas pautas de trabajo del departamento. El objetivo "
            "principal es mejorar la coordinación entre equipos y evitar perder "
            "tiempo en tareas duplicadas que no aportan valor al proceso. Para ello "
            "se ha preparado una guía con los pasos a seguir y los responsables de "
            "cada actividad. Les pedimos que revisen el documento con calma y que "
            "apliquen las indicaciones desde el lunes siguiente. El equipo de apoyo "
            "estará disponible para resolver dudas o cualquier asunto relacionado "
            "con la puesta en marcha de estas pautas. La información se enviará por "
            "el mismo canal interno de siempre y también quedará publicada en el "
            "portal de la organización. Agradecemos de antemano su paciencia, su "
            "atención y su disposición a colaborar en esta mejora continua del "
            "funcionamiento general de la empresa. Sin más por el momento, quedamos "
            "a su disposición."
        ),
        "htmlBody": "",
        "headers": (
            '{"From": "comunicacion@empresa.com", '
            '"Date": "Tue, 15 Oct 2024 02:10:00 +0000"}'
        ),
        "esperada": "benigna",
    },
    # C — medio: cuerpo < 50 palabras (cuerpo_corto 0.935) → suma 0.935
    {
        "id": "correo_c",
        "subject": "Resumen de la reunión semanal",
        "recipient": "lider@empresa.com",
        "textBody": (
            "Hola: te comparto el resumen de la reunión de hoy y los pendientes de "
            "la semana entrante. Revisa el documento y me comentas cualquier "
            "sugerencia de mejora."
        ),
        "htmlBody": "",
        "headers": (
            '{"From": "lider@empresa.com", '
            '"Date": "Tue, 15 Oct 2024 10:00:00 +0000"}'
        ),
        "esperada": "media",
    },
    # D — medio: dominio externo (0.355), cuerpo ≥ 50 palabras → suma 0.355
    {
        "id": "correo_d",
        "subject": "Logística del encuentro del jueves",
        "recipient": "ana@empresa.com",
        "textBody": (
            "Buenos días: les escribimos para confirmar los detalles logísticos del "
            "encuentro del próximo jueves. El horario de registro de participantes "
            "comenzará treinta minutos antes de la apertura de la sesión principal. "
            "Los asistentes recibirán una credencial individual que deberán mostrar "
            "en el acceso a la sala de conferencias. El desayuno se servirá en el "
            "vestíbulo del edificio y el almuerzo quedará disponible en el comedor "
            "del primer piso durante el mediodía. Queremos recordarles que el uso "
            "del espacio reservado para llamadas está limitado a quince minutos por "
            "persona para no interferir con las sesiones en curso. Agradecemos su "
            "comprensión y su pronta confirmación de asistencia mediante el "
            "formulario interno antes del lunes por la mañana."
        ),
        "htmlBody": "",
        "headers": (
            '{"From": "noticias@proveedor-externo.com", '
            '"Date": "Tue, 15 Oct 2024 09:00:00 -0500"}'
        ),
        "esperada": "media",
    },
    # E — malicioso: cuerpo < 50 palabras + "demanda" (accion_legal) → suma 1.87
    {
        "id": "correo_e",
        "subject": "Citación del juzgado",
        "recipient": "usuario@empresa.com",
        "textBody": (
            "Citación judicial: ha sido seleccionado para comparecer ante el "
            "juzgado. Debe atender de inmediato o se presentará una demanda formal "
            "en su contra."
        ),
        "htmlBody": "",
        "headers": (
            '{"From": "tribunal@correo-ejemplo.com", '
            '"Date": "Tue, 15 Oct 2024 14:00:00 -0500"}'
        ),
        "esperada": "maliciosa",
    },
]

ORDEN_A = ["correo_a", "correo_b", "correo_c", "correo_d", "correo_e"]
ORDEN_B = list(reversed(ORDEN_A))


def _correo(fixture: dict[str, Any]) -> EmailData:
    """Construye un EmailData a partir de un fixture sintético."""
    return EmailData(
        subject=fixture["subject"],
        recipient=fixture["recipient"],
        textBody=fixture["textBody"],
        htmlBody=fixture["htmlBody"],
        headers=fixture["headers"],
        message_id=fixture["id"],
    )


def _resultados_por_orden(orden: list[str]) -> dict[str, tuple[Any, ...]]:
    """Analiza los correos en el orden dado y devuelve su resultado observable."""
    por_id = {f["id"]: f for f in FIXTURES}
    resultados: dict[str, tuple[Any, ...]] = {}
    for identificador in orden:
        correo = _correo(por_id[identificador])
        score = mod_agent._genetic_score(correo)["score"]
        reporte = mod_agent.analyze_email(correo)
        resultados[identificador] = (
            score,
            reporte.es_phishing,
            reporte.nivel_severidad,
            tuple(reporte.indicadores_phishing),
        )
    return resultados


@pytest.mark.ac("AC-MEM-02")
def test_los_correos_cubren_las_tres_rutas_del_pipeline() -> None:
    """La banda de score de cada correo es la esperada (ruta benigna, agente y maliciosa).

    Garantiza además que el algoritmo genético real se está ejecutando: si
    genetic_logic no estuviera disponible, el fallback 50.0 rompería estas
    aserciones de banda.
    """
    bandas = {
        f["id"]: mod_agent._genetic_score(_correo(f))["score"] for f in FIXTURES
    }
    assert bandas["correo_a"] < 30, f"correo_a debe ser benigno: {bandas}"
    assert bandas["correo_b"] < 30, f"correo_b debe ser benigno: {bandas}"
    assert 30 <= bandas["correo_c"] <= 75, f"correo_c debe ir al agente: {bandas}"
    assert 30 <= bandas["correo_d"] <= 75, f"correo_d debe ir al agente: {bandas}"
    assert bandas["correo_e"] > 75, f"correo_e debe ser malicioso: {bandas}"


@pytest.mark.ac("AC-MEM-02")
def test_resultado_identico_en_dos_ordenes_de_analisis(
    agente_react_falso: Any, sin_red_jira: None, entorno_sin_mongo: None
) -> None:
    """SC-001: el resultado de cada correo no depende de qué correos se analizaron antes.

    El fixture `entorno_sin_mongo` elimina MONGODB_ATLAS_CLUSTER_URI: con la
    memoria conversacional presente, la ruta del agente lanza ValueError —
    rojo esperado (research D7). Tras la eliminación, ninguna ruta lee estado
    previo y ambas órdenes coinciden.
    """
    resultado_a = _resultados_por_orden(ORDEN_A)
    resultado_b = _resultados_por_orden(ORDEN_B)

    assert set(resultado_a) == set(ORDEN_A)
    for identificador in ORDEN_A:
        assert resultado_a[identificador] == resultado_b[identificador], (
            f"{identificador} cambió de resultado según el orden de análisis: "
            f"{resultado_a[identificador]} != {resultado_b[identificador]}"
        )
