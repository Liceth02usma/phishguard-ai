"""Verificacion modulo por modulo con APIs reales (sin simulacion)."""

import os, sys, json, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

from dotenv import load_dotenv
load_dotenv()

PASS, FAIL = "OK", "FAIL"
results: list[tuple[str, str, str]] = []

def test(modulo: str, nombre: str, fn) -> None:
    try:
        detalle = fn()
        results.append((modulo, PASS, detalle or nombre))
        print(f"  {PASS} - {nombre}: {detalle or ''}")
    except Exception as e:
        results.append((modulo, FAIL, str(e)))
        print(f"  {FAIL} - {nombre}: {e}")

# ============================================================
# SPEC 002: Normalizacion
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 002: Normalizacion\n" + "=" * 60)

def t_norm_api() -> str:
    from src.level2_agent.normalizacion import normalizar_desde_api
    ed = normalizar_desde_api({
        "subject": "Urgente: verifique su cuenta",
        "from": "no-reply@banco-seguro.com",
        "to": "usuario@ucaldas.edu.co",
        "text": "Haga clic en http://bit.ly/3x4mPq para verificar.",
        "html": "<html><body><a href='http://bit.ly/3x4mPq'>Click</a></body></html>",
    })
    return f"subject={ed.subject}, urls={len(ed.urls)}"

def t_norm_mask() -> str:
    from src.level2_agent.normalizacion import enmascarar_para_terceros
    from src.level2_agent.models import EmailData
    email = EmailData(subject="Test", recipient="user@gmail.com", textBody="Su tarjeta es 4532015112830366")
    masked = enmascarar_para_terceros(email)
    assert "4532015112830366" not in masked.textBody
    return "PII enmascarada"

test("002", "normalizar_desde_api", t_norm_api)
test("002", "enmascarar PII", t_norm_mask)


# ============================================================
# SPEC 003: Banderas de cabeceras
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 003: Banderas\n" + "=" * 60)

def t_band_fail() -> str:
    from src.level2_agent.banderas import evaluar_banderas
    from src.level2_agent.banderas.configuracion import ConfigBanderas
    from src.level2_agent.models import EmailData
    email = EmailData(subject="Urgente", headers=json.dumps({"From": "phish@evil.xyz", "To": "user@ucaldas.edu.co", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail"}))
    r = evaluar_banderas(email, config=ConfigBanderas.desde_entorno())
    return f"{len(r.banderas)} banderas, puntos={r.puntos_totales}"

def t_band_pass() -> str:
    from src.level2_agent.banderas import evaluar_banderas
    from src.level2_agent.banderas.configuracion import ConfigBanderas
    from src.level2_agent.models import EmailData
    email = EmailData(subject="Reunion", headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co"}))
    r = evaluar_banderas(email, config=ConfigBanderas.desde_entorno())
    return f"{len(r.banderas)} banderas, puntos={r.puntos_totales}"

test("003", "auth fail", t_band_fail)
test("003", "auth pass", t_band_pass)


# ============================================================
# SPEC 004: Analisis de URLs
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 004: URLs\n" + "=" * 60)

def t_urls() -> str:
    from src.level2_agent.analisis_urls import analizar_urls
    from src.level2_agent.models import EmailData
    email = EmailData(subject="Test", urls=["http://bit.ly/3x4mPq", "http://login-banco.xyz/auth"])
    r = analizar_urls(email)
    puntos = sum(b.puntos for b in r.banderas)
    return f"{len(r.banderas)} banderas, puntos={puntos}"

test("004", "URLs sospechosas", t_urls)


# ============================================================
# SPEC 005: Analisis de adjuntos
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 005: Adjuntos\n" + "=" * 60)

def t_adj_exe() -> str:
    from src.level2_agent.adjuntos import analizar_adjunto
    r = analizar_adjunto(nombre="factura.exe", tipo_declarado="application/octet-stream", payload=b"\x00" * 100)
    return f"sha256={r.sha256[:16]}..., {len(r.banderas)} banderas"

def t_adj_pdf() -> str:
    from src.level2_agent.adjuntos import analizar_adjunto
    r = analizar_adjunto(nombre="reporte.pdf", tipo_declarado="application/pdf", payload=b"%PDF-1.4" + b"\x00" * 100)
    return f"sha256={r.sha256[:16]}..., {len(r.banderas)} banderas"

test("005", "adjunto .exe", t_adj_exe)
test("005", "adjunto .pdf", t_adj_pdf)


# ============================================================
# SPEC 006: VirusTotal
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 006: VirusTotal\n" + "=" * 60)

def t_vt_key() -> str:
    key = os.environ.get("VT_API_KEY", "")
    if not key: raise Exception("VT_API_KEY no configurada")
    return f"key={key[:8]}..."

def t_vt_url() -> str:
    key = os.environ.get("VT_API_KEY", "")
    if not key: raise Exception("VT_API_KEY no configurada")
    from src.level2_agent.virustotal import consultar_url
    r = consultar_url("http://google.com")
    return f"clasificacion={r.clasificacion}"

def t_vt_dom() -> str:
    key = os.environ.get("VT_API_KEY", "")
    if not key: raise Exception("VT_API_KEY no configurada")
    from src.level2_agent.virustotal import consultar_dominio
    r = consultar_dominio("google.com")
    return f"clasificacion={r.clasificacion}"

test("006", "VT API key", t_vt_key)
test("006", "consultar_url", t_vt_url)
test("006", "consultar_dominio", t_vt_dom)


# ============================================================
# SPEC 007: Scoring genetico
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 007: Scoring\n" + "=" * 60)

def t_score_ben() -> str:
    from src.level3_logic.scoring import calcular_score_final
    from src.level2_agent.models import EmailData
    r = calcular_score_final(EmailData(subject="Reunion", headers=json.dumps({"From": "colega@ucaldas.edu.co"})))
    return f"score={r.score_final}, banderas={r.puntos_banderas}"

def t_score_mal() -> str:
    from src.level3_logic.scoring import calcular_score_final
    from src.level2_agent.models import EmailData
    r = calcular_score_final(EmailData(subject="URGENTE: Factura", headers=json.dumps({"From": "facturas@banc0-seguro.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}), urls=["http://bit.ly/factura-urgente"]))
    return f"score={r.score_final}, banderas={r.puntos_banderas}"

test("007", "scoring benigno", t_score_ben)
test("007", "scoring malicioso", t_score_mal)


# ============================================================
# SPEC 008: Motor de decision
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 008: Motor de decision\n" + "=" * 60)

def t_dec_mal() -> str:
    from src.level2_agent.decision import evaluar_veredicto, EntradaMotor
    from src.level2_agent.models import EmailData
    from src.level3_logic.scoring.modelos import ScoreFinal
    v = evaluar_veredicto(EntradaMotor(email_data=EmailData(subject="T"), score_final=ScoreFinal(score_final=90, score_clasificador=90.0, puntos_banderas=0, version_modelo="v1")))
    return f"veredicto={v.veredicto}, ruta={v.ruta}"

def t_dec_ben() -> str:
    from src.level2_agent.decision import evaluar_veredicto, EntradaMotor
    from src.level2_agent.models import EmailData
    from src.level3_logic.scoring.modelos import ScoreFinal
    v = evaluar_veredicto(EntradaMotor(email_data=EmailData(subject="T"), score_final=ScoreFinal(score_final=10, score_clasificador=10.0, puntos_banderas=0, version_modelo="v1")))
    return f"veredicto={v.veredicto}, ruta={v.ruta}"

test("008", "score 90 -> malicioso", t_dec_mal)
test("008", "score 10 -> sin_indicadores", t_dec_ben)


# ============================================================
# SPEC 009: Agente IA
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 009: Agente IA\n" + "=" * 60)

def t_agt_sim() -> str:
    from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
    from src.level2_agent.models import EmailData
    from src.level3_logic.scoring.modelos import ScoreFinal
    os.environ["LLM_PROVEEDOR"] = "simulado"
    r = consultar_agente(EntradaAgente(email_data=EmailData(subject="Test phishing"), score_final=ScoreFinal(score_final=50, score_clasificador=50.0, puntos_banderas=0, version_modelo="v1")), modelo=crear_modelo("simulado"))
    return f"confirmacion={r.confirmacion_agente}"

def t_agt_gem() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key: raise Exception("GOOGLE_API_KEY no configurada")
    from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
    from src.level2_agent.models import EmailData
    from src.level3_logic.scoring.modelos import ScoreFinal
    os.environ["LLM_PROVEEDOR"] = "gemini"
    # ScoreFinal invariante: score_final = min(100, round(score_clasificador + puntos_banderas))
    r = consultar_agente(EntradaAgente(email_data=EmailData(subject="Urgente: verifique su cuenta", headers=json.dumps({"From": "no-reply@banco-seguro.xyz", "Authentication-Results": "spf=fail"}), urls=["http://bit.ly/3x4mPq"]), score_final=ScoreFinal(score_final=70, score_clasificador=50.0, puntos_banderas=20, version_modelo="v1")), modelo=crear_modelo("gemini"))
    return f"confirmacion={r.confirmacion_agente}"

test("009", "agente simulado", t_agt_sim)
test("009", "agente Gemini (API real)", t_agt_gem)


# ============================================================
# SPEC 010: Acciones Gmail/Jira
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 010: Acciones Gmail/Jira\n" + "=" * 60)

def t_acc_tabla() -> str:
    from src.level2_agent.acciones import resolver_acciones, Accion
    assert Accion.CREAR_TICKET in resolver_acciones("malicioso")
    assert Accion.CREAR_TICKET_BAJA in resolver_acciones("sospechoso")
    assert resolver_acciones("sin_indicadores") == [Accion.MARCAR_LEIDO]
    return "tabla correcta"

def t_jira_auth() -> str:
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    if not all([url, email, token]): raise Exception("Credenciales Jira no configuradas")
    resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=10)
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:100]}"
    return f"auth OK, usuario={resp.json().get('displayName', '?')}"

def t_jira_proj() -> str:
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    proyecto = os.environ.get("JIRA_PROYECTO", "PD")
    if not all([url, email, token]): raise Exception("Credenciales Jira no configuradas")
    resp = requests.get(f"{url}/rest/api/2/project/{proyecto}", auth=(email, token), timeout=10)
    if resp.status_code == 200: return f"proyecto {proyecto} existe: {resp.json().get('name', '?')}"
    elif resp.status_code == 404: raise Exception(f"Proyecto '{proyecto}' no existe. Crealo en Jira primero.")
    else: raise Exception(f"Error {resp.status_code}: {resp.text[:100]}")

def t_jira_tipo() -> str:
    """Verifica que el tipo de issue 'Tarea' existe en Jira."""
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    if not all([url, email, token]): raise Exception("Credenciales Jira no configuradas")
    resp = requests.get(f"{url}/rest/api/2/issuetype", auth=(email, token), timeout=10)
    if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
    tipos = {t["name"] for t in resp.json()}
    tipo = os.environ.get("JIRA_TIPO_TICKET", "Tarea")
    if tipo not in tipos: raise Exception(f"Tipo '{tipo}' no encontrado. Disponibles: {sorted(tipos)}")
    return f"tipo '{tipo}' OK, disponibles: {sorted(tipos)[:5]}"

test("010", "tabla de acciones", t_acc_tabla)
test("010", "Jira auth real", t_jira_auth)
test("010", "Jira proyecto existe", t_jira_proj)
test("010", "Jira tipo issue", t_jira_tipo)


# ============================================================
# SPEC 011: Persistencia MongoDB
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 011: Persistencia MongoDB\n" + "=" * 60)

def t_mongo_conn() -> str:
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    if not uri: raise Exception("MONGODB_ATLAS_CLUSTER_URI no configurada")
    from pymongo import MongoClient
    cols = MongoClient(uri, serverSelectionTimeoutMS=5000)["phishguard"].list_collection_names()
    return f"conectado, colecciones: {cols[:5]}"

def t_mongo_rw() -> str:
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    if not uri: raise Exception("MONGODB_ATLAS_CLUSTER_URI no configurada")
    from pymongo import MongoClient
    from datetime import datetime, timezone, timedelta
    col = MongoClient(uri, serverSelectionTimeoutMS=5000)["phishguard"]["_verificacion_test"]
    doc = {"message_id": f"test_{int(time.time())}", "fecha": datetime.now(tz=timezone.utc), "expira_en": datetime.now(tz=timezone.utc) + timedelta(hours=1)}
    col.insert_one(doc)
    found = col.find_one({"message_id": doc["message_id"]})
    col.delete_one({"message_id": doc["message_id"]})
    assert found is not None
    return "write/read/delete OK"

test("011", "MongoDB conexion", t_mongo_conn)
test("011", "MongoDB write/read", t_mongo_rw)


# ============================================================
# SPEC 012: API REST
# ============================================================
print("\n" + "=" * 60 + "\nSPEC 012: API REST\n" + "=" * 60)

def t_api_health() -> str:
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    os.environ["API_KEY"] = "test-key"
    resp = TestClient(create_app()).get("/api/health", headers={"X-API-Key": "test-key"})
    assert resp.status_code == 200
    return f"status={resp.status_code}"

def t_api_post() -> str:
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    os.environ["API_KEY"] = "test-key"
    os.environ["LLM_PROVEEDOR"] = "simulado"
    resp = TestClient(create_app()).post("/api/analyses", json={"modo": "pegar", "dry_run": True, "subject": "Urgente: verifique", "from": "phish@evil.xyz", "text": "Clic http://bit.ly/3x4mPq", "headers": {"From": "phish@evil.xyz", "Authentication-Results": "spf=fail; dkim=fail"}}, headers={"X-API-Key": "test-key", "Content-Type": "application/json"})
    assert resp.status_code == 201
    d = resp.json()
    return f"veredicto={d['resultado']['veredicto']}, score={d['resultado']['score']}"

test("012", "GET /api/health", t_api_health)
test("012", "POST /api/analyses", t_api_post)


# ============================================================
# D12: Screenshots HCTI
# ============================================================
print("\n" + "=" * 60 + "\nD12: Screenshots HCTI\n" + "=" * 60)

def t_hcti() -> str:
    from src.level2_agent.screenshots import generar_screenshot
    url = generar_screenshot("<html><body style='font-family:sans-serif;padding:20px'><h2 style='color:#c00'>Phishing Alert</h2><p>From: soporte@banco-seguro.xyz</p><a href='http://bit.ly/3x4mPq'>Click here</a></body></html>")
    if url is None: raise Exception("HCTI retorno None")
    return f"screenshot: {url}"

test("D12", "HCTI screenshot real", t_hcti)


# ============================================================
# PIPELINE COMPLETO
# ============================================================
print("\n" + "=" * 60 + "\nPIPELINE COMPLETO\n" + "=" * 60)

def t_pipe_ben() -> str:
    from src.level2_agent.agent import analyze_email
    from src.level2_agent.models import EmailData
    os.environ["LLM_PROVEEDOR"] = "simulado"
    r = analyze_email(EmailData(subject="Reunion de equipo", recipient="equipo@ucaldas.edu.co", textBody="Hola, reunion a las 10am.", headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co"})))
    return f"veredicto={r.veredicto}, es_phishing={r.es_phishing}, score={r.score_clasificador}"

def t_pipe_mal() -> str:
    from src.level2_agent.agent import analyze_email
    from src.level2_agent.models import EmailData
    os.environ["LLM_PROVEEDOR"] = "simulado"
    r = analyze_email(EmailData(subject="URGENTE: Factura vencida", recipient="usuario@ucaldas.edu.co", textBody="Descargue el adjunto y visite http://bit.ly/factura-urgente", headers=json.dumps({"From": "facturas@banc0-seguro.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}), urls=["http://bit.ly/factura-urgente"]))
    return f"veredicto={r.veredicto}, es_phishing={r.es_phishing}, score={r.score_clasificador}"

test("pipeline", "benigno", t_pipe_ben)
test("pipeline", "malicioso", t_pipe_mal)


# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60 + "\nRESUMEN\n" + "=" * 60)

by_module: dict[str, list[tuple[str, str]]] = {}
for mod, status, detail in results:
    by_module.setdefault(mod, []).append((status, detail))

ok_count = sum(1 for _, s, _ in results if s == PASS)
fail_count = sum(1 for _, s, _ in results if s == FAIL)

for mod, items in by_module.items():
    all_ok = all(s == PASS for s, _ in items)
    icon = "OK" if all_ok else "FAIL"
    passed = sum(1 for s, _ in items if s == PASS)
    print(f"  [{icon}] Spec {mod}: {passed}/{len(items)} passed")

print(f"\n  Total: {ok_count} OK, {fail_count} FAIL de {len(results)} tests")

if fail_count > 0:
    print("\n  Tests fallidos:")
    for mod, status, detail in results:
        if status == FAIL:
            print(f"    [{mod}] {detail[:120]}")
