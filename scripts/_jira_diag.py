"""Diagnostico detallado de auth Jira."""
import os, requests, base64
from dotenv import load_dotenv; load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()

print(f"URL: {url}")
print(f"Email: {email}")
print(f"Token: {token[:15]}...{token[-10:]} (len={len(token)})")

# 1. Basic Auth con requests
print("\n--- Test 1: requests auth=(email, token) ---")
resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=10)
print(f"  Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"  Body: {resp.text[:200]}")

# 2. Basic Auth manual (header)
print("\n--- Test 2: Authorization Basic header ---")
b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
resp2 = requests.get(f"{url}/rest/api/2/myself", headers={"Authorization": f"Basic {b64}"}, timeout=10)
print(f"  Status: {resp2.status_code}")
if resp2.status_code != 200:
    print(f"  Body: {resp2.text[:200]}")

# 3. Bearer token (OAuth style)
print("\n--- Test 3: Bearer token ---")
resp3 = requests.get(f"{url}/rest/api/2/myself", headers={"Authorization": f"Bearer {token}"}, timeout=10)
print(f"  Status: {resp3.status_code}")
if resp3.status_code != 200:
    print(f"  Body: {resp3.text[:200]}")

# 4. Token como password sin email
print("\n--- Test 4: auth=(email, token) con URL directa ---")
resp4 = requests.get(
    f"{url}/rest/api/2/myself",
    auth=(email, token),
    headers={"Accept": "application/json"},
    timeout=10,
)
print(f"  Status: {resp4.status_code}")
if resp4.status_code != 200:
    print(f"  Body: {resp4.text[:200]}")
else:
    print(f"  User: {resp4.json().get('displayName')}")

# 5. Check if accessible anonymously
print("\n--- Test 5: Sin auth (anonimo) ---")
resp5 = requests.get(f"{url}/rest/api/2/myself", timeout=10)
print(f"  Status: {resp5.status_code}")

# 6. Check server info
print("\n--- Test 6: Server info (public) ---")
resp6 = requests.get(f"{url}/rest/api/2/serverInfo", timeout=10)
print(f"  Status: {resp6.status_code}")
if resp6.status_code == 200:
    info = resp6.json()
    print(f"  Version: {info.get('version', '?')}")
    print(f"  Build: {info.get('buildNumber', '?')}")
    print(f"  Base URL: {info.get('baseUrl', '?')}")
