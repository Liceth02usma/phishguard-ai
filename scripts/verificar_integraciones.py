"""Script de verificacion real de Jira y HCTI con credenciales del .env."""

import os
import sys
from dotenv import load_dotenv

# Fix encoding on Windows
sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# === 1. Jira ===
print("=" * 50)
print("JIRA")
print("=" * 50)

url = os.environ.get("JIRA_INSTANCE_URL", "")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "")

print(f"URL: {url}")
print(f"Email: {email}")
print(f"Token length: {len(token)}")
if token:
    print(f"Token prefix: {token[:10]}...")

import requests

if not all([url, email, token]):
    print("FAIL: Credenciales Jira incompletas")
else:
    try:
        auth = (email, token.strip())
        resp = requests.get(
            f"{url}rest/api/2/myself",
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"OK - Usuario: {data.get('displayName', '?')}")
            print(f"     Activo: {data.get('active', '?')}")
        else:
            print(f"FAIL - {resp.text[:200]}")
    except Exception as e:
        print(f"FAIL - Error de conexion: {e}")

# === 2. HCTI (Screenshots) ===
print()
print("=" * 50)
print("HCTI (htmlcsstoimage)")
print("=" * 50)

hcti_id = os.environ.get("HCTI_API_ID", "")
hcti_key = os.environ.get("HCTI_API_KEY", "")

print(f"API ID: {hcti_id}")
print(f"API Key: {hcti_key[:8]}...{hcti_key[-4:]}" if len(hcti_key) > 12 else f"API Key: {hcti_key}")

if not hcti_id or not hcti_key:
    print("FAIL: HCTI no configurado (credenciales vacias)")
else:
    try:
        resp = requests.post(
            "https://hcti.io/v1/image",
            auth=(hcti_id, hcti_key),
            json={"html": "<html><body style='font-family:sans-serif;padding:20px'><h2>Test PhishGuard</h2><p>Correo de prueba para verificar HCTI.</p></body></html>"},
            timeout=15,
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            img_url = data.get("url", "")
            print(f"OK - Screenshot generado: {img_url}")
        else:
            print(f"FAIL - {resp.text[:200]}")
    except Exception as e:
        print(f"FAIL - Error de conexion: {e}")

# === 3. Crear ticket de prueba en Jira ===
print()
print("=" * 50)
print("TICKET JIRA DE PRUEBA")
print("=" * 50)

if url and email and token:
    try:
        campos = {
            "fields": {
                "project": {"key": "SCRUM"},
                "issuetype": {"name": "Task"},
                "summary": "[SOC] Prueba PhishGuard-AI - Verificacion de integracion",
                "priority": {"name": "Low"},
                "description": "Ticket de prueba para verificar que la integracion Jira funciona correctamente. Puede eliminarse.",
            }
        }
        resp = requests.post(
            f"{url}rest/api/2/issue",
            json=campos,
            auth=(email, token.strip()),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 201:
            data = resp.json()
            key = data.get("key", "")
            print(f"OK - Ticket creado: {key}")
            print(f"     URL: {url}browse/{key}")
        else:
            print(f"FAIL - {resp.text[:300]}")
    except Exception as e:
        print(f"FAIL - Error: {e}")
else:
    print("SKIP: Credenciales Jira no disponibles")
