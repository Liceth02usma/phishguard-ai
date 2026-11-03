import os, sys, requests
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv()

url = os.environ.get("JIRA_INSTANCE_URL", "")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "")

resp = requests.get(
    f"{url}rest/api/2/project",
    auth=(email, token.strip()),
    headers={"Content-Type": "application/json"},
    timeout=10,
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    projects = resp.json()
    if not projects:
        print("No hay proyectos disponibles")
    for p in projects:
        key = p.get("key", "?")
        name = p.get("name", "?")
        print(f"  {key}: {name}")
else:
    print(f"Error: {resp.text[:300]}")
