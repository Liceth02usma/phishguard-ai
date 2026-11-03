"""Test Jira auth - rapido, solo 1 request."""
import os, requests
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()

print(f"Probando: {url}/rest/api/2/myself")
print(f"Email: {email}")
print(f"Token (len={len(token)}): {token[:12]}...{token[-8:]}")

resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=15)
print(f"\nStatus: {resp.status_code}")
print(f"Headers: {dict(resp.headers)[:200] if hasattr(dict(resp.headers), '__getitem__') else 'ok'}")
print(f"Body: {resp.text[:300]}")

if resp.status_code == 401:
    print("\n>>> TOKEN INVALIDO <<<")
    print("Solucion:")
    print("1. Ir a https://id.atlassian.com/manage-profile/security/api-tokens")
    print("2. Click 'Create API token'")
    print("3. Copiar el nuevo token a .env como JIRA_API_TOKEN=...")
    print("\nNota: n8n usa credenciales OAuth (jiraSoftwareCloudApi),")
    print("no API tokens. Si quieres usar OAuth en Python, hay que")
    print("implementar flujo OAuth 2.0. Pero API tokens tambien funcionan")
    print("si estan vigentes.")
elif resp.status_code == 200:
    print(f"\n>>> AUTH OK <<<")
    print(f"Usuario: {resp.json().get('displayName')}")
