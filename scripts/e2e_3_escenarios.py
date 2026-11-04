"""Prueba E2E de los 3 escenarios contra la API REST."""
import os, requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

key = os.environ.get("API_KEY", "test-key")
base = "http://127.0.0.1:8000"

def health():
    r = requests.get(f"{base}/api/health", headers={"X-API-Key": key}, timeout=10)
    return r.status_code == 200

def test_esc(nombre, payload):
    print(f"\n{'='*60}")
    print(nombre)
    print("="*60)
    if not health():
        print("  SERVER CAIDO - reiniciando...")
        return None
    r = requests.post(f"{base}/api/analyses",
        headers={"X-API-Key": key, "Content-Type": "application/json"},
        json=payload, timeout=120)
    print(f"  Status: {r.status_code}")
    if r.status_code == 201:
        d = r.json()["resultado"]
        print(f"  veredicto:    {d['veredicto']}")
        print(f"  score:        {d['score']}")
        print(f"  es_phishing:  {d['es_phishing']}")
        print(f"  severidad:    {d['nivel_severidad']}")
        return d
    else:
        print(f"  Error: {r.text[:300]}")
        return None

# Health
print("="*60)
print("HEALTH CHECK")
print("="*60)
print(f"  Status: {'OK' if health() else 'FAIL'}")

# Esc 1
r1 = test_esc("ESCENARIO 1: CORREO LEGITIMO", {
    "modo": "pegar", "dry_run": True,
    "subject": "Reunion de equipo manana",
    "from": "colega@ucaldas.edu.co",
    "to": "equipo@ucaldas.edu.co",
    "text": "Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
    "headers": {"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co",
                "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}
})

# Esc 2
r2 = test_esc("ESCENARIO 2: CORREO SOSPECHOSO", {
    "modo": "pegar", "dry_run": True,
    "subject": "Actualizacion de su cuenta de Microsoft",
    "from": "no-reply@microsoft.com",
    "to": "usuario@ucaldas.edu.co",
    "text": "Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar.",
    "headers": {"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co",
                "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}
})

# Esc 3
r3 = test_esc("ESCENARIO 3: CORREO MALICIOSO", {
    "modo": "pegar", "dry_run": True,
    "subject": "URGENTE: Su cuenta bancaria sera suspendida",
    "from": "seguridad@banc0-internacional.xyz",
    "to": "usuario@ucaldas.edu.co",
    "text": "Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
    "headers": {"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co",
                "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail",
                "X-PHP-Originating-Script": "1234:mail.php"}
})

# Resumen
print("\n" + "="*60)
print("RESUMEN COMPARATIVO")
print("="*60)
resultados = [("Esc.1 LEGITIMO", r1), ("Esc.2 SOSPECHOSO", r2), ("Esc.3 MALICIOSO", r3)]
for nombre, r in resultados:
    if r:
        v = r["veredicto"]
        s = r["score"]
        p = r["es_phishing"]
        sv = r["nivel_severidad"]
        # Validar zona esperada
        if "LEGITIMO" in nombre:
            ok = "✅" if s < 30 and v == "sin_indicadores" else "❌"
        elif "SOSPECHOSO" in nombre:
            ok = "✅" if 30 <= s <= 75 and v in ("revision_manual", "sospechoso") else "❌"
        else:
            ok = "✅" if s > 75 and v == "malicioso" else "❌"
        print(f"  {nombre:20s} score={s:3d}  veredicto={v:20s}  phishing={str(p):5s}  sev={sv:8s}  {ok}")
    else:
        print(f"  {nombre:20s} ❌ FAIL")
