"""Prueba general de TODAS las APIs (excepto Gmail). Reporte final."""
import os, sys, json, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

OK, FAIL = "OK", "FAIL"
results = []

def test(name, fn):
    try:
        d = fn()
        results.append((name, OK, d))
        print(f"  [{OK}] {name}: {d}")
    except Exception as e:
        results.append((name, FAIL, str(e)))
        print(f"  [{FAIL}] {name}: {e}")

# ============================================================
print("=" * 60)
print("1. GOOGLE GEMINI (Agente IA)")
print("=" * 60)

def t_gemini_agente():
    from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
    from src.level2_agent.models import EmailData
    from src.level3_logic.scoring.modelos import ScoreFinal
    os.environ["LLM_PROVEEDOR"] = "gemini"
    r = consultar_agente(
        EntradaAgente(
            email_data=EmailData(subject="Urgente: verifique su cuenta", headers=json.dumps({"From": "no-reply@banco-seguro.xyz", "Authentication-Results": "spf=fail"}), urls=["http://bit.ly/3x4mPq"]),
            score_final=ScoreFinal(score_final=70, score_clasificador=50.0, puntos_banderas=20, version_modelo="v1"),
        ),
        modelo=crear_modelo("gemini"),
    )
    return f"confirmacion={r.confirmacion_agente}"

test("Agente Gemini (API real)", t_gemini_agente)

# ============================================================
print("\n" + "=" * 60)
print("2. MONGODB ATLAS")
print("=" * 60)

def t_mongo_conn():
    from pymongo import MongoClient
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    if not uri: raise Exception("URI no configurada")
    cols = MongoClient(uri, serverSelectionTimeoutMS=8000)["phishguard"].list_collection_names()
    return f"{len(cols)} colecciones"

def t_mongo_rw():
    from pymongo import MongoClient
    from datetime import datetime, timezone
    uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
    col = MongoClient(uri, serverSelectionTimeoutMS=8000)["phishguard"]["_test_api"]
    doc = {"_id": f"test_{int(time.time())}", "ts": datetime.now(tz=timezone.utc)}
    col.insert_one(doc)
    found = col.find_one({"_id": doc["_id"]})
    col.delete_one({"_id": doc["_id"]})
    assert found is not None
    return "write/read/delete OK"

test("Conexion", t_mongo_conn)
test("Write/Read/Delete", t_mongo_rw)

# ============================================================
print("\n" + "=" * 60)
print("3. VIRUSTOTAL API v3")
print("=" * 60)

def t_vt_url():
    from src.level2_agent.virustotal import consultar_url
    return f"google.com={consultar_url('http://google.com').clasificacion}"

def t_vt_dom():
    from src.level2_agent.virustotal import consultar_dominio
    return f"google.com={consultar_dominio('google.com').clasificacion}"

def t_vt_ip():
    from src.level2_agent.virustotal import consultar_ip
    return f"8.8.8.8={consultar_ip('8.8.8.8').clasificacion}"

test("consultar_url", t_vt_url)
test("consultar_dominio", t_vt_dom)
test("consultar_ip", t_vt_ip)

# ============================================================
print("\n" + "=" * 60)
print("4. JIRA API")
print("=" * 60)

def t_jira_auth():
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    if not all([url, email, token]): raise Exception("Credenciales no configuradas")
    resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=15)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: Token invalido/expirado")
    return f"usuario={resp.json().get('displayName')}"

def t_jira_proyecto():
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    resp = requests.get(f"{url}/rest/api/2/project", auth=(email, token), timeout=10)
    if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
    projects = resp.json()
    if not projects: raise Exception("No hay proyectos. Crear 'Phishing Dashboard' (key=PD)")
    return f"{[p['key'] for p in projects]}"

def t_jira_tipo():
    import requests
    url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_USER_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    resp = requests.get(f"{url}/rest/api/2/issuetype", auth=(email, token), timeout=10)
    if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
    tipos = sorted(t["name"] for t in resp.json())
    if "Tarea" not in tipos: raise Exception(f"'Tarea' no encontrado. Disponibles: {tipos}")
    return f"Tarea OK, todos: {tipos[:5]}"

test("Autenticacion", t_jira_auth)
test("Proyecto PD existe", t_jira_proyecto)
test("Tipo 'Tarea' existe", t_jira_tipo)

# ============================================================
print("\n" + "=" * 60)
print("5. HCTI (htmlcsstoimage)")
print("=" * 60)

def t_hcti():
    from src.level2_agent.screenshots import generar_screenshot
    url = generar_screenshot("<html><body style='font-family:sans-serif;padding:20px'><h2>Test</h2></body></html>")
    if url is None: raise Exception("generar_screenshot retorno None")
    return f"url={url}"

test("Generar screenshot", t_hcti)

# ============================================================
print("\n" + "=" * 60)
print("6. API REST (FastAPI)")
print("=" * 60)

def t_api_health():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    os.environ["API_KEY"] = "test-key"
    resp = TestClient(create_app()).get("/api/health", headers={"X-API-Key": "test-key"})
    assert resp.status_code == 200
    return f"status={resp.status_code}"

def t_api_analyses():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    os.environ["API_KEY"] = "test-key"
    os.environ["LLM_PROVEEDOR"] = "simulado"
    resp = TestClient(create_app()).post("/api/analyses", json={"modo": "pegar", "dry_run": True, "subject": "Urgente: verifique", "from": "phish@evil.xyz", "text": "Clic http://bit.ly/3x4mPq", "headers": {"From": "phish@evil.xyz", "Authentication-Results": "spf=fail; dkim=fail"}}, headers={"X-API-Key": "test-key", "Content-Type": "application/json"})
    assert resp.status_code == 201
    d = resp.json()
    return f"veredicto={d['resultado']['veredicto']}, score={d['resultado']['score']}"

test("GET /api/health", t_api_health)
test("POST /api/analyses", t_api_analyses)

# ============================================================
print("\n" + "=" * 60)
print("7. PIPELINE COMPLETO (Gemini real)")
print("=" * 60)

def t_pipeline_mal():
    from src.level2_agent.agent import analyze_email
    from src.level2_agent.models import EmailData
    os.environ["LLM_PROVEEDOR"] = "gemini"
    r = analyze_email(EmailData(subject="URGENTE: Su cuenta sera suspendida", recipient="usuario@ucaldas.edu.co", textBody="Visite http://bit.ly/verificar-cuenta inmediatamente.", headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail"}), urls=["http://bit.ly/verificar-cuenta"]))
    return f"veredicto={r.veredicto}, score={r.score_clasificador}, severidad={r.nivel_severidad}"

test("Malicioso (Gemini real)", t_pipeline_mal)

# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
print("RESUMEN FINAL")
print("=" * 60)

ok = sum(1 for _, s, _ in results if s == OK)
fail = sum(1 for _, s, _ in results if s == FAIL)

for name, status, detail in results:
    icon = OK if status == OK else FAIL
    print(f"  [{icon}] {name}")

print(f"\n  Total: {ok} OK, {fail} FAIL de {len(results)} tests")

if fail > 0:
    print(f"\n  *** APIs FALLIDAS ({fail}) ***")
    for name, status, detail in results:
        if status == FAIL:
            print(f"    - {name}: {detail[:120]}")
