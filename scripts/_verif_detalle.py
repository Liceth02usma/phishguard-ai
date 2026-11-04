"""Verificar campos detallados de la API response."""
import os, requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()
key = os.environ.get("API_KEY", "test-key")
base = "http://127.0.0.1:8000"

for nombre, payload in [
    ("Esc.1 LEGITIMO", {
        "modo": "pegar", "dry_run": True,
        "subject": "Reunion de equipo manana",
        "from": "colega@ucaldas.edu.co",
        "to": "equipo@ucaldas.edu.co",
        "text": "Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
        "headers": {"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co",
                    "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}
    }),
    ("Esc.3 MALICIOSO", {
        "modo": "pegar", "dry_run": True,
        "subject": "URGENTE: Su cuenta bancaria sera suspendida",
        "from": "seguridad@banc0-internacional.xyz",
        "to": "usuario@ucaldas.edu.co",
        "text": "Estimado cliente> cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
        "headers": {"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co",
                    "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail",
                    "X-PHP-Originating-Script": "1234:mail.php"}
    }),
]:
    print("=" * 60)
    print(nombre)
    print("=" * 60)
    r = requests.post(f"{base}/api/analyses",
        headers={"X-API-Key": key, "Content-Type": "application/json"},
        json=payload, timeout=120)
    res = r.json()["resultado"]
    print(f"  Score: {res['score']}")
    print(f"  Veredicto: {res['veredicto']}")
    print(f"  Version modelo: {res['version_modelo']}")
    print(f"  Auth: {json.dumps(res['autenticacion'])}")
    print(f"  Banderas ({len(res['banderas'])}):")
    for b in res["banderas"]:
        print(f"    {b['codigo']:25s} sev={b['severidad']:8s} pts={b['puntos']}")
    print(f"  URLs ({len(res['urls'])}): {[u['url'] for u in res['urls']]}")
    print(f"  Indicadores ({len(res['indicadores'])}): {[i['codigo'] for i in res['indicadores']]}")
    print(f"  Analisis tecnico: {res['analisis_tecnico'][:80]}...")
