"""Verificacion con APIs externas: VT, Gemini, Jira."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

# === 006 VirusTotal ===
print("SPEC 006: VirusTotal (API real)")
vt_key = os.environ.get("VT_API_KEY", "")
if not vt_key:
    print("  SKIP - VT_API_KEY no configurada")
else:
    print(f"  OK - VT API key: {vt_key[:8]}...")
    try:
        from src.level2_agent.virustotal import consultar_url, consultar_dominio
        r1 = consultar_url("http://google.com")
        print(f"  OK - consultar_url google.com: clasificacion={r1.clasificacion}")
    except Exception as e:
        print(f"  FAIL - consultar_url: {e}")
    try:
        from src.level2_agent.virustotal import consultar_dominio
        r2 = consultar_dominio("google.com")
        print(f"  OK - consultar_dominio google.com: clasificacion={r2.clasificacion}")
    except Exception as e:
        print(f"  FAIL - consultar_dominio: {e}")

# === 009 Gemini ===
print("\nSPEC 009: Agente Gemini (API real)")
gem_key = os.environ.get("GOOGLE_API_KEY", "")
if not gem_key:
    print("  SKIP - GOOGLE_API_KEY no configurada")
else:
    try:
        from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
        from src.level2_agent.models import EmailData
        from src.level3_logic.scoring.modelos import ScoreFinal
        os.environ["LLM_PROVEEDOR"] = "gemini"
        entrada = EntradaAgente(
            email_data=EmailData(
                subject="Urgente: verifique su cuenta bancaria",
                headers=json.dumps({"From": "no-reply@banco-seguro.xyz", "Authentication-Results": "spf=fail"}),
                urls=["http://bit.ly/3x4mPq"],
            ),
            score_final=ScoreFinal(score_final=70, score_clasificador=50.0, puntos_banderas=20, version_modelo="v1"),
        )
        modelo = crear_modelo("gemini")
        r = consultar_agente(entrada, modelo=modelo)
        print(f"  OK - Gemini: confirmacion={r.confirmacion_agente}, resumen={r.salida.resumen[:60] if r.salida else 'N/A'}...")
    except Exception as e:
        print(f"  FAIL - Gemini: {e}")

# === 010 Jira ===
print("\nSPEC 010: Jira (API real)")
import requests
jira_url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
jira_email = os.environ.get("JIRA_USER_EMAIL", "")
jira_token = os.environ.get("JIRA_API_TOKEN", "").strip()

if not all([jira_url, jira_email, jira_token]):
    print("  SKIP - Credenciales Jira no configuradas")
else:
    # Auth
    try:
        resp = requests.get(f"{jira_url}/rest/api/2/myself", auth=(jira_email, jira_token), timeout=10)
        if resp.status_code == 200:
            user = resp.json().get("displayName", "?")
            print(f"  OK - Jira auth: usuario={user}")
        else:
            print(f"  FAIL - Jira auth: HTTP {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        print(f"  FAIL - Jira auth: {e}")

    # Proyectos
    try:
        resp = requests.get(f"{jira_url}/rest/api/2/project", auth=(jira_email, jira_token), timeout=10)
        if resp.status_code == 200:
            projects = resp.json()
            if projects:
                for p in projects:
                    print(f"  OK - Proyecto: key={p['key']}, name={p['name']}")
            else:
                print("  WARN - No hay proyectos. Crear 'Phishing Dashboard' con key PD en Jira.")
        else:
            print(f"  FAIL - Listar proyectos: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  FAIL - Listar proyectos: {e}")

    # Tipos de issue
    try:
        resp = requests.get(f"{jira_url}/rest/api/2/issuetype", auth=(jira_email, jira_token), timeout=10)
        if resp.status_code == 200:
            tipos = {t["name"] for t in resp.json()}
            print(f"  OK - Tipos de issue: {sorted(tipos)}")
            if "Tarea" in tipos:
                print("  OK - Tipo 'Tarea' disponible")
            else:
                print(f"  WARN - Tipo 'Tarea' no encontrado. Usar uno de: {sorted(tipos)}")
        else:
            print(f"  FAIL - Tipos de issue: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  FAIL - Tipos de issue: {e}")

# === Pipeline completo con Gemini ===
print("\nPIPELINE: analyze_email con Gemini real")
if not gem_key:
    print("  SKIP - GOOGLE_API_KEY no configurada")
else:
    try:
        from src.level2_agent.agent import analyze_email
        from src.level2_agent.models import EmailData
        os.environ["LLM_PROVEEDOR"] = "gemini"
        email = EmailData(
            subject="URGENTE: Su cuenta bancaria sera suspendida",
            recipient="usuario@ucaldas.edu.co",
            textBody="Estimado cliente, su cuenta sera suspendida. Visite http://bit.ly/verificar-cuenta inmediatamente.",
            headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
            urls=["http://bit.ly/verificar-cuenta"],
        )
        r = analyze_email(email)
        print(f"  OK - Pipeline Gemini: veredicto={r.veredicto}, es_phishing={r.es_phishing}, score={r.score_clasificador}")
    except Exception as e:
        print(f"  FAIL - Pipeline Gemini: {e}")

print("\n=== Verificacion externa completada ===")
