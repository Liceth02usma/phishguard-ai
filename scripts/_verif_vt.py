"""VT API real test (solo consultar_url)."""
import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

print("SPEC 006: VirusTotal (API real)")
from src.level2_agent.virustotal import consultar_url, consultar_dominio

r1 = consultar_url("http://google.com")
print(f"  OK - consultar_url google.com: clasificacion={r1.clasificacion}")

r2 = consultar_dominio("google.com")
print(f"  OK - consultar_dominio google.com: clasificacion={r2.clasificacion}")

r3 = consultar_url("http://evil-phishing-site.xyz/login")
print(f"  OK - consultar_url phishing: clasificacion={r3.clasificacion}")
