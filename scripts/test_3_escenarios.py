"""Prueba de los 3 escenarios contra la API REST levantada."""
import os, requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

key = os.environ.get("API_KEY", "test-key")
base = "http://127.0.0.1:8000"

# Health
print("=" * 60)
print("HEALTH CHECK")
print("=" * 60)
r = requests.get(f"{base}/api/health", headers={"X-API-Key": key}, timeout=10)
print(f"  Status: {r.status_code}, Body: {r.json()}")

# ============================================================
print("\n" + "=" * 60)
print("ESCENARIO 1: CORREO LEGITIMO")
print("=" * 60)
r1 = requests.post(f"{base}/api/analyses", headers={"X-API-Key": key, "Content-Type": "application/json"}, json={
    "modo": "pegar", "dry_run": True,
    "subject": "Reunion de equipo manana",
    "from": "colega@ucaldas.edu.co",
    "to": "equipo@ucaldas.edu.co",
    "text": "Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
    "headers": {"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}
}, timeout=120)
print(f"  Status: {r1.status_code}")
if r1.status_code == 201:
    d = r1.json()["resultado"]
    print(f"  veredicto: {d['veredicto']}")
    print(f"  score: {d['score']}")
    print(f"  es_phishing: {d['es_phishing']}")
    print(f"  severidad: {d['nivel_severidad']}")
    print(f"  ruta: {d['ruta']}")
    print(f"  banderas: {len(d['banderas'])}")
    print(f"  resumen: {d.get('resumen', '')[:80]}...")
else:
    print(f"  Error: {r1.text[:300]}")

# ============================================================
print("\n" + "=" * 60)
print("ESCENARIO 2: CORREO SOSPECHOSO")
print("=" * 60)
r2 = requests.post(f"{base}/api/analyses", headers={"X-API-Key": key, "Content-Type": "application/json"}, json={
    "modo": "pegar", "dry_run": True,
    "subject": "Actualizacion de su cuenta de Microsoft",
    "from": "no-reply@microsoft.com",
    "to": "usuario@ucaldas.edu.co",
    "text": "Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar.",
    "headers": {"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}
}, timeout=120)
print(f"  Status: {r2.status_code}")
if r2.status_code == 201:
    d = r2.json()["resultado"]
    print(f"  veredicto: {d['veredicto']}")
    print(f"  score: {d['score']}")
    print(f"  es_phishing: {d['es_phishing']}")
    print(f"  severidad: {d['nivel_severidad']}")
    print(f"  ruta: {d['ruta']}")
    print(f"  banderas: {len(d['banderas'])}")
    print(f"  resumen: {d.get('resumen', '')[:80]}...")
else:
    print(f"  Error: {r2.text[:300]}")

# ============================================================
print("\n" + "=" * 60)
print("ESCENARIO 3: CORREO MALICIOSO")
print("=" * 60)
r3 = requests.post(f"{base}/api/analyses", headers={"X-API-Key": key, "Content-Type": "application/json"}, json={
    "modo": "pegar", "dry_run": True,
    "subject": "URGENTE: Su cuenta bancaria sera suspendida",
    "from": "seguridad@banc0-internacional.xyz",
    "to": "usuario@ucaldas.edu.co",
    "text": "Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
    "headers": {"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}
}, timeout=120)
print(f"  Status: {r3.status_code}")
if r3.status_code == 201:
    d = r3.json()["resultado"]
    print(f"  veredicto: {d['veredicto']}")
    print(f"  score: {d['score']}")
    print(f"  es_phishing: {d['es_phishing']}")
    print(f"  severidad: {d['nivel_severidad']}")
    print(f"  ruta: {d['ruta']}")
    print(f"  banderas: {len(d['banderas'])}")
    print(f"  resumen: {d.get('resumen', '')[:80]}...")
    print(f"  reglas: {d.get('reglas_aplicadas', [])}")
else:
    print(f"  Error: {r3.text[:300]}")

# ============================================================
print("\n" + "=" * 60)
print("RESUMEN COMPARATIVO")
print("=" * 60)
for i, r in enumerate([r1, r2, r3], 1):
    if r.status_code == 201:
        d = r.json()["resultado"]
        print(f"  Esc.{i}: veredicto={d['veredicto']:20s} score={d['score']:3d} phishing={d['es_phishing']} sev={d['nivel_severidad']}")
    else:
        print(f"  Esc.{i}: FAIL ({r.status_code})")
