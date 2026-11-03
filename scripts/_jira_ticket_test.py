"""Jira: crear ticket de prueba y verificar."""
import os, sys, requests
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()
auth = (email, token)
proyecto = os.environ.get("JIRA_PROYECTO", "SCRUM")
tipo = os.environ.get("JIRA_TIPO_TICKET", "Tarea")

print(f"Creando ticket en proyecto={proyecto}, tipo={tipo}")

resp = requests.post(
    f"{url}/rest/api/2/issue",
    json={
        "fields": {
            "project": {"key": proyecto},
            "issuetype": {"name": tipo},
            "summary": "[TEST] PhishGuard-AI - verificacion de integracion",
            "priority": {"name": "High"},
            "description": "h2. Ticket de Prueba\n\nEste ticket fue creado automaticamente por PhishGuard-AI para verificar la integracion con Jira.\n\n* Proyecto: {proyecto}\n* Tipo: {tipo}\n\nSe puede eliminar despues de la verificacion.",
        }
    },
    auth=auth,
    headers={"Content-Type": "application/json"},
    timeout=15,
)

print(f"Status: {resp.status_code}")
if resp.status_code in (200, 201):
    data = resp.json()
    key = data.get("key", "?")
    print(f"Ticket creado: {key}")
    print(f"URL: {url}/browse/{key}")
    
    # Delete it
    print(f"\nEliminando ticket de prueba...")
    del_resp = requests.delete(f"{url}/rest/api/2/issue/{key}", auth=auth, timeout=10)
    print(f"Delete: {del_resp.status_code} ({'OK' if del_resp.status_code == 204 else 'FAIL'})")
else:
    print(f"Error: {resp.text[:300]}")
