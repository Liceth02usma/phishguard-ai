"""Diagnostico completo: clasificador + banderas + score final con cabeceras correctas."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

from src.level2_agent.models import EmailData, Cabecera
from src.level3_logic.scoring import calcular_score_final
from src.level3_logic.genetic_logic import evaluate
from src.level2_agent.banderas import evaluar_banderas, ConfigBanderas

def make_cabeceras(headers_dict):
    """Convierte dict de headers a list[Cabecera]."""
    return [Cabecera(nombre=k, valor=v) for k, v in headers_dict.items()]

scenarios = {
    "Esc.1 LEGITIMO": lambda: EmailData(
        subject="Reunion de equipo manana",
        recipient="equipo@ucaldas.edu.co",
        textBody="Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
        headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}),
        cabeceras=make_cabeceras({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"}),
    ),
    "Esc.2 SOSPECHOSO": lambda: EmailData(
        subject="Actualizacion de su cuenta de Microsoft",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar.",
        headers=json.dumps({"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}),
        cabeceras=make_cabeceras({"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"}),
    ),
    "Esc.3 MALICIOSO": lambda: EmailData(
        subject="URGENTE: Su cuenta bancaria sera suspendida",
        recipient="usuario@ucaldas.edu.co",
        textBody="Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026",
        headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
        cabeceras=make_cabeceras({"From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co", "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
        urls=["http://bit.ly/verificar-cuenta-2026"],
    ),
}

for name, make_email in scenarios.items():
    email = make_email()
    print("=" * 60)
    print(name)
    print("=" * 60)

    # 1. Clasificador lineal puro
    result = evaluate(email.model_dump())
    score_clasif = result["score"]
    genes = [g["caracteristica"] for g in result.get("genes_implicados", [])]
    print(f"  Clasificador lineal: {score_clasif:.2f}")
    print(f"  Genes activos: {genes}")

    # 2. Banderas
    config_band = ConfigBanderas.desde_entorno()
    resultado_band = evaluar_banderas(email, config=config_band)
    print(f"  Banderas ({len(resultado_band.banderas)}):")
    for b in resultado_band.banderas:
        print(f"    {b.codigo:20s} sev={b.severidad} pts={b.puntos}")
    print(f"  Puntos banderas: {resultado_band.puntos_totales}")
    print(f"  Auth: spf={resultado_band.estados_autenticacion.spf} dkim={resultado_band.estados_autenticacion.dkim} dmarc={resultado_band.estados_autenticacion.dmarc}")

    # 3. Score final compuesto
    sf = calcular_score_final(email)
    print(f"  Score final: {sf.score_final}")
    print(f"  Score clasif: {sf.score_clasificador}")
    print(f"  Puntos banderas: {sf.puntos_banderas}")

    # 4. Veredicto esperado
    if sf.score_final < 30:
        veredicto = "sin_indicadores (< 30)"
    elif sf.score_final <= 75:
        veredicto = "zona_gris (30-75)"
    else:
        veredicto = "malicioso (> 75)"
    print(f"  Veredicto: {veredicto}")
