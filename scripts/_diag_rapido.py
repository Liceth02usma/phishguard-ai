"""Diagnostico rapido: clasificador + banderas (sin URL/RDAP)."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

from src.level2_agent.models import EmailData, Cabecera
from src.level3_logic.genetic_logic import evaluate
from src.level2_agent.banderas import evaluar_banderas, ConfigBanderas

def make_cabeceras(headers_dict):
    return [Cabecera(nombre=k, valor=v) for k, v in headers_dict.items()]

scenarios = {
    "Esc.1 LEGITIMO": EmailData(
        subject="Reunion de equipo manana",
        recipient="equipo@ucaldas.edu.co",
        textBody="Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
        headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}),
        cabeceras=make_cabeceras({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}),
    ),
    "Esc.2 SOSPECHOSO": EmailData(
        subject="Actualizacion de su cuenta de Microsoft",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar.",
        headers=json.dumps({"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}),
        cabeceras=make_cabeceras({"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}),
    ),
    "Esc.3 MALICIOSO": EmailData(
        subject="URGENTE: Su cuenta bancaria sera suspendida",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
        headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
        cabeceras=make_cabeceras({"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
        urls=["http://bit.ly/verificar-cuenta-2026"],
    ),
}

for name, email in scenarios.items():
    print("=" * 60)
    print(name)
    print("=" * 60)

    # 1. Clasificador lineal
    result = evaluate(email.model_dump())
    score_clasif = result["score"]
    genes = [g["caracteristica"] for g in result.get("genes_implicados", [])]
    print(f"  Clasificador: {score_clasif:.2f}")
    print(f"  Genes: {genes}")

    # 2. Banderas (sin RDAP)
    config_band = ConfigBanderas.desde_entorno()
    from datetime import UTC, datetime
    from src.level2_agent.banderas.rdap import ClienteRDAP
    # Use a no-op RDAP client to avoid network
    class RDAPDummy:
        def registrar_evento(self, dominio): return None
    resultado_band = evaluar_banderas(email, config=config_band, ahora=datetime.now(UTC), cliente_rdap=RDAPDummy())
    print(f"  Banderas ({len(resultado_band.banderas)}):")
    for b in resultado_band.banderas:
        print(f"    {b.codigo:20s} sev={b.severidad} pts={b.puntos}")
    print(f"  Puntos banderas: {resultado_band.puntos_totales}")
    print(f"  Auth: spf={resultado_band.estados_autenticacion.spf} dkim={resultado_band.estados_autenticacion.dkim} dmarc={resultado_band.estados_autenticacion.dmarc}")

    # 3. Score estimado (clasif + banderas, sin URLs)
    score_est = min(100, round(score_clasif + resultado_band.puntos_totales))
    print(f"  Score estimado (sin URLs): {score_est}")

    if score_est < 30:
        veredicto = "sin_indicadores (< 30) ✅"
    elif score_est <= 75:
        veredicto = "zona_gris (30-75) ✅"
    else:
        veredicto = "malicioso (> 75) ✅"
    print(f"  Veredicto: {veredicto}")
