"""Jira auth diagnostic."""
import os, requests
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()

print(f"URL: {url}")
print(f"Email: {email}")
print(f"Token length: {len(token)}")

# Test auth
resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=10)
print(f"\nAuth status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  User: {data.get('displayName')}")
    print(f"  Account ID: {data.get('accountId')}")

    # List projects
    resp2 = requests.get(f"{url}/rest/api/2/project", auth=(email, token), timeout=10)
    projects = resp2.json() if resp2.status_code == 200 else []
    print(f"\n  Projects ({len(projects)}):")
    for p in projects:
        print(f"    key={p['key']}, name={p['name']}, id={p['id']}")

    # Issue types
    resp3 = requests.get(f"{url}/rest/api/2/issuetype", auth=(email, token), timeout=10)
    if resp3.status_code == 200:
        tipos = resp3.json()
        print(f"\n  Issue types ({len(tipos)}):")
        for t in tipos:
            print(f"    name={t['name']}, id={t['id']}")
elif resp.status_code == 401:
    print("  ERROR: Token invalido o expirado.")
    print("  ACCION: Generar nuevo token en:")
    print(f"    {url}/plugins/servlet/applinks/identityProviderAndAccess")
    print("  O en: https://id.atlassian.com/manage-profile/security/api-tokens")
else:
    print(f"  Body: {resp.text[:200]}")
