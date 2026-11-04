"""Escenario 3: correo malicioso con dry_run=false."""
import os, requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

key = os.environ.get("API_KEY", "test-key")
base = "http://127.0.0.1:8000"

r = requests.post(f"{base}/api/analyses",
    headers={"X-API-Key": key, "Content-Type": "application/json"},
    json={
        "modo": "pegar", "dry_run": False,
        "subject": "URGENTE: Su cuenta bancaria sera suspendida",
        "from": "seguridad@banc0-internacional.xyz",
        "to": "usuario@ucaldas.edu.co",
        "text": "Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
        "headers": {
            "From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail",
            "X-PHP-Originating-Script": "1234:mail.php"
        }
    }, timeout=120)

d = r.json()
res = d["resultado"]
print(f"Status: {r.status_code}")
print(f"Score: {res['score']}")
print(f"Veredicto: {res['veredicto']}")
print(f"Es phishing: {res['es_phishing']}")
print(f"Severidad: {res['nivel_severidad']}")
print(f"Auth: {json.dumps(res['autenticacion'])}")
print(f"Banderas ({len(res['banderas'])}):")
for b in res["banderas"]:
    print(f"  {b['codigo']:25s} sev={b['severidad']:8s} pts={b['puntos']}")
print(f"URLs ({len(res['urls'])}): {[u['url'] for u in res['urls']]}")
print(f"Indicadores ({len(res['indicadores'])}): {[i['codigo'] for i in res['indicadores']]}")
print(f"Version modelo: {res['version_modelo']}")
print(f"Resumen: {res['resumen'][:200]}")
print(f"Acciones: ejecutada={d['accion']['ejecutada']} simulada={d['accion']['simulada']}")
ticket = res.get("ticket")
if ticket:
    print(f"Ticket Jira: {ticket['clave']} -> {ticket['url']}")
else:
    print("Ticket Jira: (ninguno)")
