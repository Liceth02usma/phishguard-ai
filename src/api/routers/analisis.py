"""Router de análisis: POST/GET/GET{id}/PATCH/DELETE /api/analyses (spec 012).

FR-001: endpoints de análisis.
AC-API-03: dry_run activo por defecto.
AC-API-10: caída VT → 201 con revision_manual.
"""

from __future__ import annotations

import io
import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from src.api.analisis_conversor import (
    analizar_adjuntos_eml,
    headers_como_dict,
    persistido_a_response,
    ruta_desde_score,
)
from src.api.config import (
    LIMITE_PAGINACION_DEFAULT,
    LIMITE_PAGINACION_MAX,
    MULTIPART_MAX_BYTES,
)
from src.api.csv_export import generar_csv
from src.api.deps import APIKeyDep, CacheVTDep, RepoDep
from src.api.eml_parser import parsear_eml, quitar_etiquetas_html
from src.api.errors import EntradaGrandeError, NoEncontradoError
from src.api.routers.muestras import leer_fixture
from src.api.schemas.analisis import (
    AdjuntoResponse,
    AnalisisMuestraRequest,
    AnalisisPaginadoResponse,
    AnalisisPegarRequest,
    AnalisisResponse,
    FeedbackRequest,
)
from src.api.schemas.comunes import Severidad, Veredicto
from src.level2_agent.persistencia.borrado import borrar_analisis
from src.level2_agent.persistencia.guardado import guardar_analisis
from src.level2_agent.persistencia.modelos import AnalisisPersistido

router = APIRouter(prefix="/analyses", tags=["Analisis"])


@router.post("", status_code=201, response_model=AnalisisResponse)
async def post_analyses(
    request: Request,
    _: APIKeyDep,
    repo: RepoDep,
) -> AnalisisResponse:
    """Analizar un correo (modos pegar, muestra y eml; AC-API-03 dry_run default)."""
    content_type = request.headers.get("content-type", "")

    # Campos comunes que cada modo debe poblar (A1/A2/A3).
    destinatario = ""
    cuerpo_html = ""
    headers_dict: dict[str, str] = {}

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
        # A3: parsear el EML real. Antes se metía el MIME crudo en textBody
        # con remitente="(eml)" y sin cabeceras, así que el mismo correo
        # daba resultados distintos en modo pegar y en modo eml.
        eml = parsear_eml(contenido)
        nombre_archivo = getattr(archivo, "filename", None) or "(sin nombre)"
        if eml.asunto and eml.asunto != "(sin asunto)":
            asunto = eml.asunto
        else:
            asunto = f"EML: {nombre_archivo}"
        remitente = eml.remitente
        destinatario = eml.destinatario
        cuerpo_html = eml.cuerpo_html
        cuerpo_texto = eml.cuerpo_texto or quitar_etiquetas_html(eml.cuerpo_html)
        headers_dict = dict(eml.cabeceras)
        # AC-API-02: extraer adjuntos del EML y analizar con spec 005
        adjuntos_resp: list[AdjuntoResponse] = analizar_adjuntos_eml(contenido)
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
            # A1: analizar el contenido REAL del fixture. Antes se analizaba
            # un stub (asunto "Muestra: x", cuerpo vacío, de muestra@test.com)
            # y los tres escenarios salían siempre score=31 -> sospechoso.
            fx = leer_fixture(body.muestra)
            if fx is None:
                asunto = f"Muestra: {body.muestra}"
                remitente = "(desconocido)"
                cuerpo_texto = ""
            else:
                headers_dict = headers_como_dict(fx.get("headers"))
                asunto = str(fx.get("subject") or f"Muestra: {body.muestra}")
                remitente = headers_dict.get("from") or "(desconocido)"
                destinatario = str(fx.get("recipient") or "")
                cuerpo_texto = str(fx.get("textBody") or "")
                cuerpo_html = str(fx.get("htmlBody") or "")
        else:
            asunto = body.subject or "(sin asunto)"
            remitente = body.from_ or "(desconocido)"
            destinatario = body.to or ""
            cuerpo_texto = body.text or ""
            cuerpo_html = body.html or ""
            headers_dict = headers_como_dict(body.headers)
        adjuntos_resp = []

    # Ejecutar pipeline completo (specs 003-009)
    report = None
    resultado_band = None
    score_final_obj = None
    email_data = None
    try:
        from src.level2_agent.agent import analyze_email
        from src.level2_agent.models import Cabecera, EmailData

        # Construir headers como JSON string y cabeceras para el pipeline
        headers_json = (
            json.dumps(headers_dict, ensure_ascii=False) if headers_dict else ""
        )
        cabeceras_list = [
            Cabecera(nombre=k, valor=v) for k, v in headers_dict.items()
        ]

        email_data = EmailData(
            subject=asunto,
            # A2: el destinatario es `to`, no el remitente. Con
            # recipient=from se perdía el gen dominio_externo (el de mayor
            # peso, +2.26) y un phishing real caía de 100 a 71.
            recipient=destinatario or remitente,
            textBody=cuerpo_texto,
            htmlBody=cuerpo_html,
            headers=headers_json,
            cabeceras=cabeceras_list,
        )
        report = analyze_email(email_data)
        veredicto = report.veredicto
        score = int(report.score_final or report.score_clasificador or 0)
        resumen = report.resumen
        # Normalizar severidad: el pipeline usa "Crítico" con tilde,
        # pero AnalisisPersistido usa "Critico" sin tilde
        severidad = report.nivel_severidad
        if severidad == "Crítico":
            severidad = "Critico"

        # Evaluar banderas por separado para exponer autenticación
        try:
            from src.level2_agent.banderas import evaluar_banderas
            from src.level2_agent.banderas.configuracion import ConfigBanderas
            config_band = ConfigBanderas.desde_entorno()
            resultado_band = evaluar_banderas(email_data, config=config_band)
        except Exception:
            pass

        # Obtener score_final_obj del agente (para banderas de scoring)
        # Solo si no lo tenemos ya del report
        if score_final_obj is None:
            try:
                from src.level3_logic.scoring import calcular_score_final
                score_final_obj = calcular_score_final(email_data)
            except Exception:
                pass

    except Exception:
        # AC-API-10: caída → 201 con revision_manual
        veredicto = "revision_manual"
        score = 0
        resumen = "Error en el análisis; requiere revisión manual."
        severidad = "Medio"

    duracion_ms = int((time.monotonic() - t0) * 1000)
    msg_id = f"api_{int(time.monotonic()*1000)}"

    # Persistir
    ahora = datetime.now(tz=UTC)

    analisis_p = AnalisisPersistido(
        message_id=msg_id,
        origen="api",
        modo="dry_run" if dry_run else "produccion",
        fecha=ahora,
        duracion_ms=duracion_ms,
        correo_enmascarado={"remitente": remitente, "asunto": asunto},
        score_final=score,
        ruta=ruta_desde_score(score),  # A4: derivada del score, no "ia" fijo
        veredicto=veredicto,  # type: ignore[arg-type]
        nivel_severidad=severidad,  # type: ignore[arg-type]
        version_pesos="v1",
        version_modelo="gemini-2.5-flash-lite",
        expira_en=ahora + timedelta(days=90),
    )
    guardar_analisis(analisis_p, repo=repo)

    resp = persistido_a_response(analisis_p.model_dump(mode="json"))
    # Inyectar resumen y adjuntos en la respuesta
    resp.resultado.resumen = resumen
    resp.resultado.adjuntos = adjuntos_resp

    # Poblar campos detallados del resultado
    if report is not None:
        from src.api.schemas.analisis import IndicadorResponse
        resp.resultado.indicadores = [
            IndicadorResponse(codigo=ind, descripcion=ind, peso=1.0)
            for ind in (report.indicadores_phishing or [])
        ]
        resp.resultado.analisis_tecnico = report.analisis_tecnico
        resp.resultado.justificacion_veredicto = report.justificacion_veredicto
        resp.resultado.version_modelo = report.version_modelo or "clasificador_v1"

    # Banderas de scoring (spec 003/004/005)
    if score_final_obj is not None:
        from src.api.schemas.analisis import BanderaResponse
        resp.resultado.banderas = [
            BanderaResponse(
                codigo=b.codigo, severidad=b.origen,
                puntos=b.puntos, detalle=f"{b.origen}:{b.codigo}",
            )
            for b in (score_final_obj.banderas or [])
        ]

    # Autenticación SPF/DKIM/DMARC + banderas de cabeceras
    if resultado_band is not None:
        from src.api.schemas.analisis import AutenticacionResponse, BanderaResponse
        est = resultado_band.estados_autenticacion
        resp.resultado.autenticacion = AutenticacionResponse(
            spf=est.spf, dkim=est.dkim, dmarc=est.dmarc,
        )
        codigos_existentes = {b.codigo for b in resp.resultado.banderas}
        for b in resultado_band.banderas:
            if b.codigo not in codigos_existentes:
                resp.resultado.banderas.append(BanderaResponse(
                    codigo=b.codigo, severidad=b.severidad,
                    puntos=b.puntos, detalle=b.detalle,
                ))

    # URLs del correo
    if email_data is not None:
        from src.api.schemas.analisis import UrlResponse
        # URLs del email_data + URLs extraídas del texto
        all_urls = list(email_data.urls) if email_data.urls else []
        if not all_urls and email_data.textBody:
            import re as _re
            _url_pattern = _re.compile(r'https?://\S+', _re.IGNORECASE)
            all_urls = _url_pattern.findall(email_data.textBody)
        resp.resultado.urls = [
            UrlResponse(url=u, reputacion="desconocida")
            for u in all_urls
        ]

    # Acciones ejecutadas (conectar ejecutor cuando dry_run=false)
    if report is not None and not dry_run:
        try:
            from src.level2_agent.acciones.ejecutor import ejecutar_acciones
            from src.level2_agent.acciones.jira_adapter import JiraReal
            from src.level2_agent.acciones.modelos import EntradaAcciones

            # Construir entrada completa con el reporte del pipeline
            entrada_acc = EntradaAcciones(
                message_id=msg_id,
                veredicto=veredicto,  # type: ignore[arg-type]
                nivel_severidad=severidad,  # type: ignore[arg-type]
                remitente=remitente,
                asunto=asunto,
                urls=[u.url for u in resp.resultado.urls] if resp.resultado.urls else [],
                reporte=report,
                origen="api",
            )
            resultado_acc = ejecutar_acciones(
                entrada_acc, jira=JiraReal(),
            )
            # Mapear ticket si se creó
            if resultado_acc.ticket_key:
                from src.api.schemas.analisis import TicketResponse
                jira_base = os.environ.get(
                    "JIRA_INSTANCE_URL", "https://ucaldas-team-uodce00a.atlassian.net/"
                ).rstrip("/")
                clave = resultado_acc.ticket_key
                resp.resultado.ticket = TicketResponse(
                    clave=clave, url=f"{jira_base}/browse/{clave}",
                )
            # Mapear acciones ejecutadas
            acciones_ejecutadas = [
                acc.accion.value for acc in resultado_acc.acciones if acc.ejecutada
            ]
            resp.accion.simulada = False
            resp.accion.ejecutada = ", ".join(acciones_ejecutadas) if acciones_ejecutadas else None
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Acciones degradadas: %s", exc)

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

    items = [persistido_a_response(d) for d in page_docs]
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
    items = [persistido_a_response(d) for d in docs]
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
    return persistido_a_response(doc)


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
    return persistido_a_response(doc)


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
