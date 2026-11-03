"""Test rapido de conectividad a todas las APIs."""
import os, sys, socket, requests
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

def dns_check(host):
    try:
        socket.getaddrinfo(host, 443)
        return True
    except:
        return False

def http_check(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code
    except Exception as e:
        return str(e)[:60]

print("=== DNS Resolution ===")
hosts = {
    "Google": "google.com",
    "Atlassian": "ucaldas-team-uodce00a.atlassian.net",
    "MongoDB Atlas": "cluster0.ygbu6dn.mongodb.net",
    "VirusTotal": "www.virustotal.com",
    "HCTI": "hcti.io",
    "Google AI": "generativelanguage.googleapis.com",
}
for name, host in hosts.items():
    ok = dns_check(host)
    print(f"  {'OK' if ok else 'FAIL'} - {name}: {host}")

print("\n=== HTTP Reachability ===")
apis = {
    "Google": "https://google.com",
    "Atlassian /myself": f"{os.environ.get('JIRA_INSTANCE_URL', '').rstrip('/')}/rest/api/2/serverInfo",
    "VirusTotal": "https://www.virustotal.com/api/v3",
    "HCTI": "https://hcti.io",
    "Google AI": "https://generativelanguage.googleapis.com/",
}
for name, url in apis.items():
    status = http_check(url)
    print(f"  {'OK' if isinstance(status, int) else 'FAIL'} - {name}: {status}")

print("\n=== API Key Checks ===")
keys = {
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
    "MONGODB_ATLAS_CLUSTER_URI": os.environ.get("MONGODB_ATLAS_CLUSTER_URI", ""),
    "VT_API_KEY": os.environ.get("VT_API_KEY", ""),
    "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN", ""),
    "HCTI_API_ID": os.environ.get("HCTI_API_ID", ""),
    "HCTI_API_KEY": os.environ.get("HCTI_API_KEY", ""),
}
for name, val in keys.items():
    ok = len(val) > 0
    print(f"  {'OK' if ok else 'MISSING'} - {name}: {'*' * min(len(val), 12)} (len={len(val)})")
