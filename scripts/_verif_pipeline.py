"""Pipeline completo con Gemini real."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

from src.level2_agent.agent import analyze_email
from src.level2_agent.models import EmailData

os.environ["LLM_PROVEEDOR"] = "gemini"

# Correo malicioso
email_mal = EmailData(
    subject="URGENTE: Su cuenta bancaria sera suspendida",
    recipient="usuario@ucaldas.edu.co",
    textBody="Estimado cliente, su cuenta sera suspendida. Visite http://bit.ly/verificar-cuenta inmediatamente.",
    headers=json.dumps({"From": "seguridad@banc0-internacional.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}),
    urls=["http://bit.ly/verificar-cuenta"],
)
r1 = analyze_email(email_mal)
print(f"Malicioso: veredicto={r1.veredicto}, es_phishing={r1.es_phishing}, score={r1.score_clasificador}")
print(f"  resumen={r1.resumen[:80]}...")
print(f"  severidad={r1.nivel_severidad}")

# Correo benigno
email_ben = EmailData(
    subject="Reunion de equipo manana a las 10am",
    recipient="equipo@ucaldas.edu.co",
    textBody="Hola equipo, recuerden la reunion de manana. Saludos.",
    headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co"}),
)
r2 = analyze_email(email_ben)
print(f"\nBenigno: veredicto={r2.veredicto}, es_phishing={r2.es_phishing}, score={r2.score_clasificador}")
print(f"  resumen={r2.resumen[:80]}...")
print(f"  severidad={r2.nivel_severidad}")
