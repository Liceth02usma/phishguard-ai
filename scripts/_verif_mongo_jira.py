"""MongoDB + Jira verificacion directa."""
import os, requests
from dotenv import load_dotenv; load_dotenv()

# --- MongoDB ---
print("MONGODB ATLAS")
uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
try:
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client["phishguard"]
    cols = db.list_collection_names()
    print(f"  OK - Conexion: {len(cols)} colecciones: {cols[:6]}")
    # Write test
    from datetime import datetime, timezone, timedelta
    import time as t
    col = db["_test_api"]
    doc = {"_id": f"test_{int(t.time())}", "ts": datetime.now(tz=timezone.utc)}
    col.insert_one(doc)
    found = col.find_one({"_id": doc["_id"]})
    col.delete_one({"_id": doc["_id"]})
    print(f"  OK - Write/Read/Delete: {'OK' if found else 'FAIL'}")
except Exception as e:
    print(f"  FAIL - {e}")

# --- Jira ---
print("\nJIRA API")
url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
email = os.environ.get("JIRA_USER_EMAIL", "")
token = os.environ.get("JIRA_API_TOKEN", "").strip()

# Auth
try:
    resp = requests.get(f"{url}/rest/api/2/myself", auth=(email, token), timeout=10)
    if resp.status_code == 200:
        print(f"  OK - Auth: usuario={resp.json().get('displayName')}")
    else:
        print(f"  FAIL - Auth: HTTP {resp.status_code}")
except Exception as e:
    print(f"  FAIL - Auth: {e}")

# Projects (with proper auth check)
try:
    resp = requests.get(f"{url}/rest/api/2/project", auth=(email, token), timeout=10)
    if resp.status_code == 200:
        projects = resp.json()
        print(f"  OK - Proyectos ({len(projects)}): {[p['key'] for p in projects]}")
        if not projects:
            print(f"  WARN - No hay proyectos. Crear 'Phishing Dashboard' (key=PD) en Jira.")
    else:
        print(f"  FAIL - Proyectos: HTTP {resp.status_code}")
except Exception as e:
    print(f"  FAIL - Proyectos: {e}")

# Issue types
try:
    resp = requests.get(f"{url}/rest/api/2/issuetype", auth=(email, token), timeout=10)
    if resp.status_code == 200:
        tipos = sorted(t["name"] for t in resp.json())
        print(f"  OK - Tipos de issue: {tipos}")
    else:
        print(f"  FAIL - Tipos: HTTP {resp.status_code}")
except Exception as e:
    print(f"  FAIL - Tipos: {e}")
