"""Analisis del clasificador: genes activados y calibracion."""
import os, sys, json, math
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

from src.level2_agent.models import EmailData
from src.level3_logic.genetic_logic import ConfigGenetico, evaluate, MAPEO_INDICES
from src.level3_logic.modelo import cargar_modelo

m = json.load(open("data/modelo/clasificador_v1.json"))
coefs = m["coeficientes"]
intercept = m["intercepto"]
model = cargar_modelo()

# ============================================================
print("=" * 60)
print("COEFICIENTES TOP (|peso| > 0.5)")
print("=" * 60)
for name, w in sorted(coefs.items(), key=lambda x: abs(x[1]), reverse=True):
    if abs(w) > 0.5:
        print(f"  {name:35s} {w:+.4f}")
print(f"  {'intercepto':35s} {intercept:+.4f}")

# ============================================================
print("\n" + "=" * 60)
print("GENES ACTIVADOS POR CADA ESCENARIO")
print("=" * 60)

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
    result = evaluate(email.model_dump())
    score = result["score"]
    genes_list = result.get("genes_implicados", [])

    # Also compute manually
    genes_vec = [0] * 32
    for g in genes_list:
        if g in MAPEO_INDICES:
            genes_vec[MAPEO_INDICES.index(g)] = 1

    z = intercept + sum(coefs.get(MAPEO_INDICES[i], 0) * genes_vec[i] for i in range(32))
    manual_score = 100 * (1 / (1 + math.exp(-z)))

    print(f"\n--- {name} ---")
    print(f"  Score pipeline: {score:.2f}")
    print(f"  Score manual:   {manual_score:.2f}")
    print(f"  z (suma lineal): {z:.4f}")
    print(f"  Genes activos ({len(genes_list)}): {genes_list}")

    # Show each gene contribution
    print(f"  Contribuciones:")
    for g in genes_list:
        w = coefs.get(g, 0)
        print(f"    {g:35s} w={w:+.4f}")

# ============================================================
print("\n" + "=" * 60)
print("DIAGNOSTICO: POR QUE ESC.1 DA SCORE ALTO?")
print("=" * 60)
email1 = scenarios["Esc.1 LEGITIMO"]
result1 = evaluate(email1.model_dump())
genes1 = result1.get("genes_implicados", [])
print(f"Genes activos en correo legitimo: {genes1}")
print(f"Score: {result1['score']:.2f}")
print(f"\nEl problema: estos genes se activan incorrectamente:")
for g in genes1:
    w = coefs.get(g, 0)
    print(f"  - {g}: peso={w:+.4f} (contribuye {w:+.4f} a z)")

# ============================================================
print("\n" + "=" * 60)
print("DATOS DE ENTRENAMIENTO")
print("=" * 60)
import pandas as pd
df = pd.read_csv("100correos.csv")
print(f"Total: {len(df)} correos")
print(f"Columnas: {list(df.columns)[:15]}...")
# Check label distribution
for col in ["es_phishing", "label", "phishing", "tipo"]:
    if col in df.columns:
        print(f"Distribucion '{col}': {df[col].value_counts().to_dict()}")
