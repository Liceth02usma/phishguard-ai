"""Jira full verification."""
import os, sys, json, requests
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()
auth = (email, token)

# Auth
resp = requests.get(f"{url}/rest/api/2/myself", auth=auth, timeout=15)
print(f"1. Auth: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"   Usuario: {data.get('emailAddress', '?')}")
    print(f"   AccountID: {data.get('accountId', '?')}")
else:
    print(f"   FAIL: {resp.text[:200]}")
    sys.exit(1)

# Projects
resp2 = requests.get(f"{url}/rest/api/2/project", auth=auth, timeout=10)
print(f"\n2. Proyectos: {resp2.status_code}")
if resp2.status_code == 200:
    projects = resp2.json()
    print(f"   Total: {len(projects)}")
    for p in projects:
        print(f"   - key={p['key']}, name={p['name']}, id={p['id']}")
    
    # Check if PD exists
    pd_exists = any(p['key'] == 'PD' for p in projects)
    if not pd_exists:
        print("\n   >>> Proyecto PD no existe. Intentando crearlo...")
        create_resp = requests.post(
            f"{url}/rest/api/2/project",
            json={
                "key": "PD",
                "name": "Phishing Dashboard",
                "projectTypeKey": "software",
                "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-scrum-template",
                "leadAccountId": data.get('accountId', ''),
            },
            auth=auth,
            timeout=15,
        )
        print(f"   Create status: {create_resp.status_code}")
        if create_resp.status_code in (200, 201):
            print(f"   Proyecto PD creado exitosamente!")
        else:
            print(f"   Error: {create_resp.text[:300]}")
            # Try with different template
            print("\n   Intentando con template 'com.atlassian.jira:jira-blank-project'...")
            create_resp2 = requests.post(
                f"{url}/rest/api/2/project",
                json={
                    "key": "PD",
                    "name": "Phishing Dashboard",
                    "projectTypeKey": "business",
                    "projectTemplateKey": "com.atlassian.jira:jira-blank-project",
                    "leadAccountId": data.get('accountId', ''),
                },
                auth=auth,
                timeout=15,
            )
            print(f"   Create status: {create_resp2.status_code}")
            if create_resp2.status_code in (200, 201):
                print(f"   Proyecto PD creado exitosamente!")
            else:
                print(f"   Error: {create_resp2.text[:300]}")
else:
    print(f"   FAIL: {resp2.text[:200]}")

# Issue types
resp3 = requests.get(f"{url}/rest/api/2/issuetype", auth=auth, timeout=10)
print(f"\n3. Tipos de issue: {resp3.status_code}")
if resp3.status_code == 200:
    tipos = resp3.json()
    for t in tipos:
        print(f"   - name={t['name']}, id={t['id']}, subtask={t.get('subtask', False)}")
    
    tarea_exists = any(t['name'] == 'Tarea' for t in tipos)
    task_exists = any(t['name'] == 'Task' for t in tipos)
    if tarea_exists:
        print(f"\n   Tipo 'Tarea' disponible!")
    elif task_exists:
        print(f"\n   Tipo 'Tarea' NO existe, pero 'Task' si. Actualizando JIRA_TIPO_TICKET...")
        os.environ["JIRA_TIPO_TICKET"] = "Task"
    else:
        print(f"\n   Ni 'Tarea' ni 'Task' encontrados. Disponibles: {[t['name'] for t in tipos]}")

# Create test ticket
print(f"\n4. Test crear ticket...")
proyecto_key = "PD"
# Check if PD exists now
resp_proj = requests.get(f"{url}/rest/api/2/project", auth=auth, timeout=10)
projects = resp_proj.json() if resp_proj.status_code == 200 else []
pd_exists = any(p['key'] == 'PD' for p in projects)

if pd_exists:
    # Find Tarea or Task type
    tipo_name = "Tarea" if tarea_exists else ("Task" if task_exists else tipos[0]['name'] if tipos else "Task")
    ticket_resp = requests.post(
        f"{url}/rest/api/2/issue",
        json={
            "fields": {
                "project": {"key": "PD"},
                "issuetype": {"name": tipo_name},
                "summary": "[TEST] PhishGuard-AI verificacion",
                "description": "Ticket de prueba para verificar la integracion Jira. Se puede eliminar.",
            }
        },
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    print(f"   Create ticket: {ticket_resp.status_code}")
    if ticket_resp.status_code in (200, 201):
        issue = ticket_resp.json()
        issue_key = issue.get('key', '?')
        print(f"   Ticket creado: {issue_key}")
        print(f"   URL: {url}/browse/{issue_key}")
        
        # Delete test ticket
        del_resp = requests.delete(f"{url}/rest/api/2/issue/{issue_key}", auth=auth, timeout=10)
        print(f"   Delete ticket: {del_resp.status_code} ({'OK' if del_resp.status_code == 204 else 'FAIL'})")
    else:
        print(f"   Error: {ticket_resp.text[:300]}")
else:
    print(f"   SKIP - Proyecto PD no existe")
