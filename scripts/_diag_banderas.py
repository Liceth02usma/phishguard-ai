"""Diagnostico: qué banderas se activan por escenario."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

from src.level2_agent.models import EmailData
from src.level2_agent.banderas import evaluar_banderas, ConfigBanderas

scenarios = {
    "Esc.1 LEGITIMO": EmailData(
        subject="Reunion de equipo manana",
        recipient="equipo@ucaldas.edu.co",
        textBody="Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
        headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"}),
    ),
    "Esc.2 SOSPECHOSO": EmailData(
        subject="Actualizacion de su cuenta de Microsoft",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar.",
        headers=json.dumps({"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "spf=pass; dkim=none; dmarc=none"}),
    ),
    "Esc.3 MALICIOSO": EmailData(
        subject="URGENTE: Su cuenta bancaria sera suspendida",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
        headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
        urls=["http://bit.ly/verificar-cuenta-2026"],
    ),
}

for name, email in scenarios.items():
    print("=" * 60)
    print(name)
    print("=" * 60)
    config = ConfigBanderas()
    resultado = evaluar_banderas(email, config=config)
    print(f"  Puntos totales: {resultado.puntos_totales}")
    print(f"  Banderas activas:")
    for b in resultado.banderas:
        print(f"    {b.codigo:20s} sev={b.severidad} pts={b.puntos} - {b.detalle}")
    print(f"  Estados autenticacion: {resultado.estados_autenticacion}")
