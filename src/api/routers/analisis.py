"""Router de análisis: POST/GET/GET{id}/PATCH/DELETE /api/analyses (spec 012).

FR-001: endpoints de análisis.
AC-API-03: dry_run activo por defecto.
AC-API-10: caída VT → 201 con revision_manual.
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from src.api.csv_export import generar_csv
from src.api.deps import APIKeyDep, CacheVTDep, RepoDep
from src.api.eml_parser import extraer_adjuntos_eml
from src.api.errors import EntradaGrandeError, NoEncontradoError
from src.api.schemas.analisis import (
    AdjuntoResponse,
    AnalisisMuestraRequest,
    AnalisisPaginadoResponse,
    AnalisisPegarRequest,
    AnalisisResponse,
    FeedbackRequest,
)
from src.api.config import (
    LIMITE_PAGINACION_DEFAULT,
    LIMITE_PAGINACION_MAX,
    MULTIPART_MAX_BYTES,
)
from src.api.schemas.comunes import Severidad, Veredicto
from src.level2_agent.persistencia.borrado import borrar_analisis
from src.level2_agent.persistencia.guardado import guardar_analisis
from src.level2_agent.persistencia.modelos import AnalisisPersistido

router = APIRouter(prefix="/analyses", tags=["Analisis"])


def _persistido_a_response(doc: dict[str, Any]) -> AnalisisResponse:
    """Convierte un documento persistido a AnalisisResponse."""
    from src.api.schemas.analisis import (
        AccionResponse,
        CorreoResponse,
        ResultadoResponse,
    )

    correo = doc.get("correo_enmascarado", {})
    resultado = doc.get("resultado", {})

    # Mapear modo de persistencia a modo de API
    modo_raw = doc.get("modo", "produccion")
    modo_api = "pegar" if modo_raw in ("produccion", "dry_run") else modo_raw

    return AnalisisResponse(
        id=str(doc.get("message_id", "")),
        origen=doc.get("origen", "api"),
        modo=modo_api,
        creado_en=doc.get("fecha", datetime.now(tz=timezone.utc)),
        duracion_ms=doc.get("duracion_ms", 0),
        correo=CorreoResponse(
            remitente=correo.get("remitente", ""),
            asunto=correo.get("asunto", ""),
            cuerpo_enmascarado=correo.get("texto_limpio", ""),
        ),
        resultado=ResultadoResponse(
            score=doc.get("score_final", 0),
            ruta=doc.get("ruta", "heuristica"),
            es_phishing=doc.get("veredicto") == "malicioso",
            veredicto=doc.get("veredicto", "sin_indicadores"),
            nivel_severidad=doc.get("nivel_severidad", "Bajo"),
            resumen=resultado.get("resumen", ""),
        ),
        accion=AccionResponse(
            ejecutada=doc.get("accion"),
            simulada=modo_raw == "dry_run",
        ),
        retroalimentacion=doc.get("retroalimentacion"),
    )


def _analizar_adjuntos_eml(contenido: bytes) -> list[AdjuntoResponse]:
    """Extrae adjuntos del EML y analiza con spec 005 (AC-API-02).

    Devuelve lista de AdjuntoResponse con SHA-256 y reputación.
    Errores de análisis de adjuntos se ignoran (degradación graceful).
    """
    from src.level2_agent.adjuntos import analizar_adjunto

    resultado: list[AdjuntoResponse] = []
    for adj in extraer_adjuntos_eml(contenido):
        try:
            analisis = analizar_adjunto(
                nombre=adj.nombre,
                tipo_declarado=adj.tipo_declarado,
                payload=adj.payload,
            )
            resultado.append(
                AdjuntoResponse(
                    nombre=analisis.nombre,
                    tipo_real=analisis.tipo_real,
                    sha256=analisis.sha256,
                    tamano=analisis.tamano_bytes,
                    reputacion="desconocida",
                )
            )
        except Exception:
            # Degradación: adjunto no analizable → omitir
            pass
    return resultado


@router.post("", status_code=201, response_model=AnalisisResponse)
async def post_analyses(
    request: Request,
    _: APIKeyDep,
    repo: RepoDep,
) -> AnalisisResponse:
    """Analizar un correo (modos pegar, muestra y eml; AC-API-03 dry_run default)."""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # Modo EML
        form = await request.form()
        _modo = str(form.get("modo", "eml"))
        dry_run = form.get("dry_run", "true") == "true"
        archivo = form.get("archivo")
        if archivo is None or not hasattr(archivo, "read"):
            raise EntradaGrandeError()
        contenido = await archivo.read()
        if len(contenido) > MULTIPART_MAX_BYTES:
            raise EntradaGrandeError()
        t0 = time.monotonic()
        asunto = f"EML: {getattr(archivo, 'filename', None) or '(sin nombre)'}"
        remitente = "(eml)"
        cuerpo_texto = contenido.decode("utf-8", errors="replace")[:2000]
        # AC-API-02: extraer adjuntos del EML y analizar con spec 005
        adjuntos_resp = _analizar_adjuntos_eml(contenido)
    else:
        # JSON body (pegar o muestra)
        body_raw = await request.json()
        if body_raw.get("modo") == "muestra":
            body: AnalisisPegarRequest | AnalisisMuestraRequest = AnalisisMuestraRequest(**body_raw)
        else:
            body = AnalisisPegarRequest(**body_raw)
        dry_run = body.dry_run
        t0 = time.monotonic()
        if isinstance(body, AnalisisMuestraRequest):
            asunto = f"Muestra: {body.muestra}"
            remitente = "muestra@test.com"
            cuerpo_texto = ""
        else:
            asunto = body.subject or "(sin asunto)"
            remitente = body.from_ or "(desconocido)"
            cuerpo_texto = body.text or ""
        adjuntos_resp: list[AdjuntoResponse] = []

    # Ejecutar pipeline (simplificado — el real usa analyze_email)
    try:
        from src.level2_agent.agent import analyze_email
        from src.level2_agent.models import EmailData

        email_data = EmailData(
            subject=asunto,
            sender=remitente,
            body=cuerpo_texto,
            headers="",
        )
        report = analyze_email(email_data)
        veredicto = "malicioso" if report.es_phishing else "sin_indicadores"
        score = int(report.score_clasificador or 0)
        resumen = report.resumen
        severidad = report.nivel_severidad
    except Exception:
        # AC-API-10: caída → 201 con revision_manual
        veredicto = "revision_manual"
        score = 0
        resumen = "Error en el análisis; requiere revisión manual."
        severidad = "Medio"

    duracion_ms = int((time.monotonic() - t0) * 1000)
    msg_id = f"api_{int(time.monotonic()*1000)}"

    # Persistir
    ahora = datetime.now(tz=timezone.utc)

    analisis_p = AnalisisPersistido(
        message_id=msg_id,
        origen="api",
        modo="dry_run" if dry_run else "produccion",
        fecha=ahora,
        duracion_ms=duracion_ms,
        correo_enmascarado={"remitente": remitente, "asunto": asunto},
        score_final=score,
        ruta="ia",
        veredicto=veredicto,  # type: ignore[arg-type]
        nivel_severidad=severidad,  # type: ignore[arg-type]
        version_pesos="v1",
        version_modelo="gemini-2.5-flash-lite",
        expira_en=ahora + timedelta(days=90),
    )
    guardar_analisis(analisis_p, repo=repo)

    resp = _persistido_a_response(analisis_p.model_dump(mode="json"))
    # Inyectar resumen y adjuntos en la respuesta
    resp.resultado.resumen = resumen  # type: ignore[union-attr]
    resp.resultado.adjuntos = adjuntos_resp
    return resp


@router.get("", response_model=AnalisisPaginadoResponse)
async def list_analyses(
    _: APIKeyDep,
    repo: RepoDep,
    veredicto: list[Veredicto] | None = Query(default=None),
    severidad: list[Severidad] | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    orden: str | None = Query(default=None, max_length=50),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(
        default=LIMITE_PAGINACION_DEFAULT, ge=1, le=LIMITE_PAGINACION_MAX
    ),
) -> AnalisisPaginadoResponse:
    """Lista paginada de análisis con filtros."""
    filtro: dict[str, Any] = {}
    if veredicto:
        filtro["veredicto"] = {"$in": veredicto}
    if severidad:
        filtro["nivel_severidad"] = {"$in": severidad}
    if q:
        filtro["q"] = q
    if desde:
        filtro["desde"] = desde.isoformat()
    if hasta:
        filtro["hasta"] = hasta.isoformat()
    if orden:
        filtro["orden"] = orden

    docs = repo.listar(filtro)
    total = len(docs)
    start = (pagina - 1) * limite
    end = start + limite
    page_docs = docs[start:end]

    items = [_persistido_a_response(d) for d in page_docs]
    return AnalisisPaginadoResponse(
        items=items, pagina=pagina, limite=limite, total=total
    )


@router.get("/export.csv")
async def export_csv(
    _: APIKeyDep,
    repo: RepoDep,
) -> StreamingResponse:
    """Exportación CSV (FR-004, AC-API-08)."""
    docs = repo.listar({})
    items = [_persistido_a_response(d) for d in docs]
    csv_content = generar_csv(items)

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analyses.csv"},
    )


@router.get("/{id}", response_model=AnalisisResponse)
async def get_analyses_by_id(
    id: str,
    _: APIKeyDep,
    repo: RepoDep,
) -> AnalisisResponse:
    """Detalle de un análisis."""
    doc = repo.buscar(id)
    if doc is None:
        raise NoEncontradoError()
    return _persistido_a_response(doc)


@router.patch("/{id}/feedback", response_model=AnalisisResponse)
async def patch_feedback(
    id: str,
    body: FeedbackRequest,
    _: APIKeyDep,
    repo: RepoDep,
) -> AnalisisResponse:
    """Retroalimentación del análisis."""
    doc = repo.buscar(id)
    if doc is None:
        raise NoEncontradoError()
    # Actualizar retroalimentación
    doc["retroalimentacion"] = body.feedback
    repo.borrar(id)
    repo.guardar(doc)
    return _persistido_a_response(doc)


@router.delete("/{id}", status_code=204)
async def delete_analyses(
    id: str,
    _: APIKeyDep,
    repo: RepoDep,
    cache_vt: CacheVTDep,
) -> None:
    """Borrado de análisis + caché VT (FR-005)."""
    borrado = borrar_analisis(id, repo=repo, cache_vt=cache_vt)
    if not borrado:
        raise NoEncontradoError()
