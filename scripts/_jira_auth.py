"""Jira auth test - directo."""
import os, requests
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()

# Auth test
print(f"Auth test: {url}/rest/api/2/myself")
resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=15)
print(f"  Status: {resp.status_code}")
print(f"  Body: {resp.text[:300]}")

if resp.status_code == 200:
    data = resp.json()
    print(f"\n  >>> AUTH OK <<<")
    print(f"  Usuario: {data.get('displayName')}")
    print(f"  AccountID: {data.get('accountId')}")

    # List projects
    resp2 = requests.get(f"{url}/rest/api/2/project", auth=(email, token), timeout=10)
    projects = resp2.json() if resp2.status_code == 200 else []
    print(f"\n  Proyectos ({len(projects)}):")
    for p in projects:
        print(f"    key={p['key']}, name={p['name']}")

    # Issue types
    resp3 = requests.get(f"{url}/rest/api/2/issuetype", auth=(email, token), timeout=10)
    if resp3.status_code == 200:
        tipos = resp3.json()
        print(f"\n  Tipos de issue ({len(tipos)}):")
        for t in tipos:
            print(f"    name={t['name']}, id={t['id']}")
elif resp.status_code == 401:
    print(f"\n  >>> TOKEN INVALIDO (401) <<<")
    print(f"  El token en .env no funciona.")
    print(f"  Solucion: regenerar en https://id.atlassian.com/manage-profile/security/api-tokens")
