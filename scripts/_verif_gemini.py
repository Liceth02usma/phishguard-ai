"""Gemini API real test."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

print("SPEC 009: Agente Gemini (API real)")
from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
from src.level2_agent.models import EmailData
from src.level3_logic.scoring.modelos import ScoreFinal

os.environ["LLM_PROVEEDOR"] = "gemini"
entrada = EntradaAgente(
    email_data=EmailData(
        subject="Urgente: verifique su cuenta bancaria",
        headers=json.dumps({"From": "no-reply@banco-seguro.xyz", "Authentication-Results": "spf=fail"}),
        urls=["http://bit.ly/3x4mPq"],
    ),
    score_final=ScoreFinal(score_final=70, score_clasificador=50.0, puntos_banderas=20, version_modelo="v1"),
)
modelo = crear_modelo("gemini")
r = consultar_agente(entrada, modelo=modelo)
print(f"  OK - confirmacion={r.confirmacion_agente}")
if r.salida:
    print(f"  OK - resumen={r.salida.resumen[:80]}...")
    print(f"  OK - justificacion={r.salida.justificacion_veredicto[:80]}...")
